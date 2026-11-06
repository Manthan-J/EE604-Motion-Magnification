"""CPU-only, ROI-guided Eulerian magnification of luminance detail."""

import argparse
from itertools import chain
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
import numpy as np
from scipy import signal

from auto_frequency import estimate_dominant_frequency, extract_roi_signal
from src.spatial import (
    build_laplacian_pyramid as decompose_laplacian,
    reconstruct_laplacian_pyramid,
    suppress_artifacts,
)


def build_gaussian_pyramid(src, level=3):
    """Return the source and its progressively downsampled versions."""
    pyramid = [src]
    for _ in range(level):
        pyramid.append(cv2.pyrDown(pyramid[-1]))
    return pyramid


def build_laplacian_pyramid(src, levels=3):
    """Return signed detail bands, ordered from coarsest to finest."""
    return decompose_laplacian(src, levels)[-2::-1]


def load_video(video_filename, *, max_decoded_bytes=None):
    """Decode the actual frames and keep fractional source FPS."""
    cap = cv2.VideoCapture(str(video_filename))
    try:
        if not cap.isOpened():
            raise ValueError(f"Could not open input video: {video_filename}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError(f"Input video has invalid FPS: {video_filename}")
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if max_decoded_bytes is not None and (len(frames) + 1) * frame.nbytes > max_decoded_bytes:
                raise ValueError("This clip is too large after decoding. Use a shorter or lower-resolution video.")
            frames.append(frame)
        if not frames:
            raise ValueError(f"No frames could be decoded: {video_filename}")
    finally:
        cap.release()
    return np.stack(frames), fps


def _bandpass_sections(low, high, fps, order):
    """Validate the passband and design numerically stable filter sections."""
    if not np.isfinite(fps) or not 0 < low < high < fps / 2:
        raise ValueError("Passband must satisfy 0 < low < high < FPS / 2.")
    return signal.butter(order, [low, high], btype="bandpass", fs=fps, output="sos")


def _filter_time(data, sections):
    """Filter offline without temporal phase lag or a zero-state startup."""
    if len(data) < 2:
        raise ValueError("Temporal filtering requires at least two frames.")
    # A bandpass has no unmatched poles or zeros at the origin.
    padlen = min(3 * (2 * len(sections) + 1), len(data) - 1)
    return signal.sosfiltfilt(sections, data, axis=0, padlen=padlen)


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    """Apply a zero-phase Butterworth bandpass along the frame axis."""
    return _filter_time(data, _bandpass_sections(lowcut, highcut, fs, order))


def make_roi_mask(frame_shape, roi):
    """Build an inward-feathered mask for an (x, y, width, height) rectangle."""
    height, width = frame_shape[:2]
    x, y, w, h = roi
    if any(not isinstance(v, (int, np.integer)) for v in roi):
        raise ValueError("ROI coordinates and size must be integers.")
    if not (0 <= x < x + w <= width and 0 <= y < y + h <= height):
        raise ValueError("ROI must have positive area and fit inside the frame.")
    mask = np.zeros((height, width), dtype=np.float32)
    weights = []
    for start, length, extent in ((x, w, width), (y, h, height)):
        # Small selections retain an interior peak; frame edges need no fade.
        feather = min(8, (length - 1) // 2)
        axis_weights = np.ones(length, dtype=np.float32)
        ramp = np.arange(1, feather + 1, dtype=np.float32) / (feather + 1)
        if feather and start > 0:
            axis_weights[:feather] = ramp
        if feather and start + length < extent:
            axis_weights[-feather:] = ramp[::-1]
        weights.append(axis_weights)
    mask[y:y + h, x:x + w] = weights[1][:, None] * weights[0]
    return mask


def select_interactive_roi(first_frame):
    """Select a rectangle on the first frame, returning None on cancellation."""
    window = "Select ROI for Magnification"
    print("Drag a box, then press Enter or Space to confirm, or C to cancel.")
    roi = cv2.selectROI(window, first_frame, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow(window)
    if not roi[2] or not roi[3]:
        return None
    return tuple(roi)


def generate_pyramid_masks(base_mask, levels):
    """Match the support of the ROI to each detail band, coarsest first."""
    # Keep feathering for the final blend so it is applied just once.
    support = (base_mask > 0).astype(np.float32)
    return build_gaussian_pyramid(support, levels - 1)[::-1]


def _magnified_frames(frames, fps, low, high, levels, amplification, base_mask,
                      artifact_suppression=False):
    """Yield magnified BGR frames after filtering their luminance details."""
    if frames.ndim != 4 or frames.shape[-1] != 3 or frames.dtype != np.uint8:
        raise ValueError("Frames must be a uint8 array with shape (time, height, width, 3).")
    if min(frames.shape[1:3]) < 1 or len(frames) < 2:
        raise ValueError("At least two nonempty frames are required.")
    max_levels = (max(frames.shape[1:3]) - 1).bit_length()
    if not isinstance(levels, (int, np.integer)) or not 1 <= levels <= max_levels:
        raise ValueError("Pyramid levels must be positive and fit the frame size.")
    if not np.isfinite(amplification) or amplification < 0:
        raise ValueError("Amplification must be finite and nonnegative.")
    sections = _bandpass_sections(low, high, fps, order=5)
    if amplification == 0 or not np.any(base_mask):
        yield from frames
        return

    masks = generate_pyramid_masks(base_mask, levels)
    bands = [np.empty((len(frames), *mask.shape), dtype=np.float32) for mask in masks]
    for i, frame in enumerate(frames):
        # Work in luminance to avoid amplifying RGB channel differences.
        gray = cv2.cvtColor(frame.astype(np.float32), cv2.COLOR_BGR2GRAY)
        for band, detail in zip(bands, build_laplacian_pyramid(gray, levels)):
            band[i] = detail

    for band, mask in zip(bands, masks):
        # Spatial strips bound the filter's float64 scratch space. Every pixel
        # still sees the entire time series, so there are no temporal seams.
        for y in range(0, band.shape[1], 16):
            strip = band[:, y:y + 16]
            strip[:] = _filter_time(strip, sections) * mask[y:y + 16]

    # Match the submitted normalized filter's color sigma in amplified pixel units.
    sigma_color = 0.1 * 255 / max(amplification, 1e-6) if artifact_suppression else None
    for i, frame in enumerate(frames):
        details = [band[i] for band in bands]
        if artifact_suppression:
            details = [suppress_artifacts(detail, sigma_color=sigma_color) for detail in details]
        # Collapse the signed details without restoring the unfiltered Gaussian base.
        residual = reconstruct_laplacian_pyramid(details[::-1])
        # Upsampling coarse bands spreads their support. Gate again at full
        # resolution so pixels outside the rectangle are exactly unchanged.
        delta = (residual * base_mask).astype(np.float64)
        with np.errstate(over="ignore"):
            delta *= amplification
        # Limit the same signed delta for all three channels to preserve their
        # differences, even when a channel would otherwise saturate.
        np.clip(delta, -frame.min(axis=2).astype(np.int16), 255 - frame.max(axis=2),
                out=delta)
        adjustment = np.rint(delta).astype(np.int16)
        yield (frame + adjustment[..., None]).astype(np.uint8)


def magnify_frames(frames, fps, low, high, roi=None, levels=3, amplification=4, *,
                   artifact_suppression=False):
    """Magnify BGR frames, optionally smoothing each filtered detail band.

    ROI=None selects the full frame. With a rectangle, pixels outside it are
    preserved even when bilateral suppression is enabled.
    """
    frames = np.asarray(frames)
    if frames.ndim != 4:
        raise ValueError("Expected frames with shape (time, height, width, 3).")
    mask = np.ones(frames.shape[1:3], dtype=np.float32)
    if roi is not None:
        mask = make_roi_mask(frames.shape[1:], roi)
    result = np.empty_like(frames)
    for i, frame in enumerate(_magnified_frames(frames, fps, low, high, levels,
                                                amplification, mask, artifact_suppression)):
        result[i] = frame
    return result


def save_video(video_tensor, fps, output_path="out_masked.avi"):
    """Write a lossless FFV1 AVI at source FPS, padding odd dimensions by one."""
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".avi":
        raise ValueError("The output path must end in .avi (FFV1 lossless video).")
    frames = iter(video_tensor)
    first = next(frames)
    height, width = first.shape[:2]
    pad_h, pad_w = height % 2, width % 2
    # OpenCV's FFmpeg writer drops the last row/column of odd-sized inputs.
    # Stage beside the destination so a failed run leaves an existing result intact.
    with NamedTemporaryFile(dir=output_path.parent, suffix=".avi", delete=False) as temp:
        staged_path = Path(temp.name)
    try:
        writer = cv2.VideoWriter(str(staged_path), cv2.VideoWriter_fourcc(*"FFV1"),
                                 fps, (width + pad_w, height + pad_h))
        try:
            if not writer.isOpened():
                raise OSError(f"Could not open video writer: {output_path}")
            for frame in chain((first,), frames):
                if pad_h or pad_w:
                    frame = cv2.copyMakeBorder(frame, 0, pad_h, 0, pad_w, cv2.BORDER_REPLICATE)
                writer.write(frame)
        finally:
            writer.release()
        staged_path.replace(output_path)
    finally:
        staged_path.unlink(missing_ok=True)


def magnify_motion_with_roi(video_name, low, high, levels=3, amplification=4, *,
                            roi=None, output_path="out_masked.avi", full_frame=False,
                            auto_search=None, frequency_channel="green"):
    """Magnify a video file, selecting the ROI interactively if omitted.

    With auto_search=(min_hz, max_hz), estimate the frequency on the original
    pixels in the same rectangle. Use low and high as the fallback band.
    """
    if Path(video_name).resolve() == Path(output_path).resolve():
        raise ValueError("Input and output must be different files.")
    if roi is not None and full_frame:
        raise ValueError("Choose either an ROI or full-frame magnification.")
    frames, fps = load_video(video_name)
    if full_frame:
        height, width = frames.shape[1:3]
        roi = (0, 0, width, height)
    elif roi is None:
        roi = select_interactive_roi(frames[0])
        if roi is None:
            return None

    mask = make_roi_mask(frames.shape[1:], roi)
    if auto_search is not None:
        # The mask weights are for blending. Estimate from the original
        # rectangle so feathering and amplification cannot bias its spectrum.
        samples = extract_roi_signal(frames, tuple(roi), channel=frequency_channel)
        estimate = estimate_dominant_frequency(samples, fps, *auto_search)
        if estimate.reliable:
            low, high = estimate.low_hz, estimate.high_hz
            print(f"Dominant ROI frequency {estimate.peak_hz:.3f} Hz "
                  f"({estimate.bpm:.1f} cycles/min). Using {low:.3f} to {high:.3f} Hz.")
        else:
            print(f"{estimate.message} Using manual band {low:.3f} to {high:.3f} Hz.")

    output_frames = _magnified_frames(frames, fps, low, high, levels, amplification, mask)
    save_video(output_frames, fps, output_path)
    return Path(output_path)


def main():
    """Run with the bundled baby clip or an explicit input and passband."""
    default_video = Path(__file__).resolve().parent / "PyEVM" / "baby.mp4"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", default=default_video)
    parser.add_argument("--output", default="out_masked.avi")
    parser.add_argument("--low", type=float, default=0.4, help="Manual or fallback low cutoff in Hz.")
    parser.add_argument("--high", type=float, default=1.0, help="Manual or fallback high cutoff in Hz.")
    parser.add_argument("--auto-frequency", action="store_true",
                        help="Estimate and use a passband from the selected ROI.")
    parser.add_argument("--search-low", type=float, default=0.65, help="Auto search minimum in Hz.")
    parser.add_argument("--search-high", type=float, default=3.0, help="Auto search maximum in Hz.")
    parser.add_argument("--frequency-channel", choices=("green", "gray", "mean"), default="green",
                        help="Intensity channel for the auto frequency estimate.")
    parser.add_argument("--levels", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=4)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--roi", nargs=4, type=int, metavar=("X", "Y", "W", "H"))
    selection.add_argument("--full-frame", action="store_true")
    args = parser.parse_args()
    auto_search = (args.search_low, args.search_high) if args.auto_frequency else None
    try:
        output = magnify_motion_with_roi(args.video, args.low, args.high, args.levels,
                                         args.alpha, roi=args.roi, output_path=args.output,
                                         full_frame=args.full_frame, auto_search=auto_search,
                                         frequency_channel=args.frequency_channel)
    except (ValueError, OSError, cv2.error) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Saved {output}" if output is not None else "Selection canceled.")


if __name__ == "__main__":
    main()
