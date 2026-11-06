"""Measure the integrated CPU pipeline and generate report tables and plots."""

import argparse
import csv
import platform
from pathlib import Path
from time import perf_counter

import cv2
import matplotlib
import numpy as np

from auto_frequency import estimate_dominant_frequency, extract_roi_signal
from roi_magnification import magnify_frames

matplotlib.use("Agg")
from matplotlib import pyplot as plt


ROOT = Path(__file__).resolve().parent
SEARCH_BAND = (0.65, 3.0)
VARIANTS = (
    ("Baseline", False, False, False),
    ("Auto band only", True, False, False),
    ("ROI only", False, True, False),
    ("Bilateral only", False, False, True),
    ("Auto band + ROI", True, True, False),
    ("Full pipeline", True, True, True),
)


def read_excerpt(path, start, seconds):
    """Decode a bounded excerpt and downscale to a maximum side of 320 pixels."""
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or not np.isfinite(fps) or fps <= 0:
            raise ValueError(f"Cannot open {path} with a valid frame rate.")
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(start * fps))
        frames = []
        for _ in range(round(seconds * fps)):
            ok, frame = cap.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            scale = min(1.0, 320 / max(width, height))
            if scale < 1:
                size = (max(1, round(width * scale)), max(1, round(height * scale)))
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            frames.append(frame)
    finally:
        cap.release()
    if len(frames) < 2:
        raise ValueError(f"Excerpt of {path} must contain at least two frames.")
    return np.stack(frames), fps, (width, height)


def rescale_roi(roi, source_size, frame_shape):
    """Convert an original-frame rectangle to the actual processing resolution."""
    x, y, width, height = roi
    src_w, src_h = source_size
    dst_h, dst_w = frame_shape[:2]
    if not (0 <= x < x + width <= src_w and 0 <= y < y + height <= src_h):
        raise ValueError("The benchmark ROI must have positive area inside the source frame.")
    x0, x1 = round(x * dst_w / src_w), round((x + width) * dst_w / src_w)
    y0, y1 = round(y * dst_h / src_h), round((y + height) * dst_h / src_h)
    if x0 == x1 or y0 == y1:
        raise ValueError("The benchmark ROI is too small after resizing.")
    return x0, y0, x1 - x0, y1 - y0


def synthetic_clip(alpha):
    """Generate noisy subpixel motion and a clean amplified-motion reference."""
    fps = 30.0
    time = np.arange(360) / fps
    motion = 0.24 * np.sin(2 * np.pi * 1.2 * time)
    x = np.arange(160)[None, :]
    rng = np.random.default_rng(604)
    frames = np.full((len(time), 80, 160), 65.0)
    clean = frames.copy()
    for target, gain in ((frames, 1), (clean, 1 + alpha)):
        edge = 65 + 105 / (1 + np.exp(-(x - 49 - gain * motion[:, None]) / 1.1))
        target[:, 17:62, :100] = edge[:, None, :100]
    frames += rng.normal(0, 1.5, frames.shape)
    frames[:, 15:65, 120:144] += (
        20 + 4 * np.sin(2 * np.pi * 0.8 * time)
    )[:, None, None]
    frames = np.repeat(np.clip(np.rint(frames), 0, 255).astype(np.uint8)[..., None], 3, axis=3)
    return frames, fps, (40, 24, 23, 30), clean


def tone_amplitude(samples, fps, hz):
    """Fit a sinusoid, constant and linear trend at a shared evaluation frequency."""
    time = np.arange(len(samples)) / fps
    angle = 2 * np.pi * hz * time
    design = np.column_stack((np.sin(angle), np.cos(angle), np.ones_like(time), time))
    coefficients = np.linalg.lstsq(design, samples, rcond=None)[0]
    return float(np.hypot(*coefficients[:2]))


def plot_space_time(path, fps, roi, slices):
    """Compare aligned horizontal slices with one grayscale range."""
    x, _, width, _ = roi
    fig, axes = plt.subplots(1, len(slices), figsize=(7.2, 2.8), sharey=True,
                             layout="constrained")
    limits = [np.percentile(np.concatenate(slices, axis=1), q) for q in (1, 99)]
    for ax, values, name in zip(axes, slices, ("Input", "Baseline", "Auto band + ROI", "Full")):
        ax.imshow(values, cmap="gray", aspect="auto", interpolation="nearest",
                  extent=(x - 0.5, x + width - 0.5, len(values) / fps, 0),
                  vmin=limits[0], vmax=limits[1])
        ax.set(title=name, xlabel="x (pixels)")
    axes[0].set_ylabel("Time (s)")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_wrist_spectrum(path, estimate):
    """Preserve the full PSD and show why a smaller in-band peak is selected."""
    fig, ax = plt.subplots(figsize=(5, 2.5), layout="constrained")
    ax.plot(estimate.frequencies, estimate.psd)
    ax.axvspan(*SEARCH_BAND, alpha=0.2, label="Search range")
    if estimate.reliable:
        ax.axvline(estimate.peak_hz, color="darkorange",
                   label=f"Selected {estimate.peak_hz:.2f} Hz")
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD")
    ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def evaluate(name, frames, fps, roi, manual_band, alpha, output, clean=None, detection_roi=None):
    """Run one-factor and matched comparisons on the same decoded frames."""
    detection_roi = roi if detection_roi is None else detection_roi
    t0 = perf_counter()
    samples = extract_roi_signal(frames, detection_roi)
    search_high = min(SEARCH_BAND[1], 0.95 * fps / 2)
    if search_high <= SEARCH_BAND[0]:
        raise ValueError("Frame rate is too low for the benchmark search range.")
    estimate = estimate_dominant_frequency(samples, fps, SEARCH_BAND[0], search_high)
    frequency_seconds = perf_counter() - t0
    auto_band = (estimate.low_hz, estimate.high_hz) if estimate.reliable else manual_band
    hz = 1.2 if clean is not None else estimate.peak_hz
    reference_amplitude = tone_amplitude(samples, fps, hz) if hz is not None else 0
    x, y, width, height = roi
    outside = np.ones(frames.shape[1:3], dtype=bool)
    outside[y:y + height, x:x + width] = False
    scan = np.s_[:, y + height // 2, x:x + width, 1]
    slices = [frames[scan].copy()]
    rows = []
    for label, auto, localized, bilateral in VARIANTS:
        band = auto_band if auto else manual_band
        t0 = perf_counter()
        result = magnify_frames(frames, fps, *band, roi=roi if localized else None,
                                amplification=alpha, artifact_suppression=bilateral)
        elapsed = perf_counter() - t0 + (frequency_seconds if auto else 0)
        # The pipeline adds the same signed change to each channel. Use green
        # here to measure leakage without including source background motion.
        squared = 0.0
        for original, processed in zip(frames, result):
            delta = processed[..., 1][outside].astype(float) - original[..., 1][outside]
            squared += np.sum(delta ** 2)
        outside_rms = np.sqrt(squared / (len(frames) * outside.sum())) if outside.any() else None
        gain = None
        if reference_amplitude > 1e-8:
            gain = tone_amplitude(extract_roi_signal(result, detection_roi), fps, hz) / reference_amplitude
        rmse = None
        if clean is not None:
            # Exclude the first and last seconds and the feathered ROI border.
            interior = np.s_[30:-30, y + 8:y + height - 8, x + 8:x + width - 8]
            rmse = np.sqrt(np.mean((result[..., 1][interior] - clean[interior]) ** 2))
        rows.append(dict(
            clip=name, variant=label, frames=len(frames), width=frames.shape[2],
            height=frames.shape[1], source_fps=fps, roi=roi, detection_roi=detection_roi,
            alpha=alpha,
            estimated_hz=estimate.peak_hz, confidence=estimate.confidence,
            estimate_status=estimate.message, low_hz=band[0], high_hz=band[1],
            outside_rms=outside_rms, tone_gain=gain, synthetic_rmse=rmse,
            seconds=elapsed, processing_fps=len(frames) / elapsed,
        ))
        if label in ("Baseline", "Auto band + ROI", "Full pipeline"):
            slices.append(result[scan].copy())
        del result
    plot_space_time(output / f"{name}-xt.png", fps, roi, slices)
    if name == "wrist":
        plot_wrist_spectrum(output / "wrist-psd.png", estimate)
    print(f"{name}: {len(frames)} frames, selected {estimate.peak_hz} Hz", flush=True)
    return rows


def write_results(output, rows):
    """Export full measurements and compact CVPR-ready tables."""
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    machine = platform.processor() or platform.machine()
    (output / "runtime-environment.txt").write_text(
        f"{platform.system()} {platform.release()} | {machine}\n"
        f"Python {platform.python_version()} | OpenCV {cv2.__version__} | "
        f"NumPy {np.__version__}\nSingle run per configuration; decoding, plotting, "
        "and encoding excluded. PSD estimation included in automatic configurations.\n",
        encoding="utf-8",
    )
    for clip in ("wrist", "synthetic"):
        selected = [row for row in rows if row["clip"] == clip]
        if not selected:
            continue
        metric = "outside_rms" if clip == "wrist" else "synthetic_rmse"
        lines = []
        for row in selected:
            gain = f'{row["tone_gain"]:.2f}' if row["tone_gain"] is not None else "--"
            lines.append(
                f'{row["variant"]} & {row[metric]:.2f} & {gain} & '
                f'{row["seconds"]:.2f} & {row["processing_fps"]:.1f} ' + r"\\"
            )
        (output / f"{clip}-table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    """Run the bundled suite, or evaluate one explicitly selected local clip."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "validation")
    parser.add_argument("--alpha", type=float, default=4)
    parser.add_argument("--video", type=Path, help="Optional private or additional benchmark clip")
    parser.add_argument("--roi", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                        help="ROI in original video pixels (required with --video)")
    parser.add_argument("--start", type=float, default=0, help="Custom excerpt start in seconds")
    parser.add_argument("--seconds", type=float, default=10, help="Custom excerpt length")
    parser.add_argument("--band", type=float, nargs=2, default=(0.7, 1.1))
    args = parser.parse_args()
    if (args.video is None) != (args.roi is None):
        parser.error("--video and --roi must be supplied together.")
    if not all(np.isfinite(v) for v in (args.start, args.seconds, args.alpha)):
        parser.error("Start, duration and alpha must be finite.")
    if args.start < 0 or args.seconds <= 0 or args.alpha < 0:
        parser.error("Use a nonnegative start and alpha and a positive duration.")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    if args.video is None:
        frames, fps, roi, clean = synthetic_clip(args.alpha)
        rows.extend(evaluate("synthetic", frames, fps, roi, (0.7, 1.1), args.alpha,
                             args.output, clean))
        clips = (
            ("wrist", ROOT / "data/derived/wrist_half_resolution.mp4",
             (174, 82, 54, 54), 30, (0.7, 1.1)),
            ("baby", ROOT / "PyEVM/baby.mp4", (340, 210, 260, 158), 10, (0.4, 1.0)),
            ("guitar", ROOT / "PyEVM/guitar.mp4", (121, 71, 183, 42), 10, (0.4, 3.0)),
        )
    else:
        clips = (("custom", args.video, args.roi, args.seconds, args.band),)
    for name, path, source_roi, seconds, band in clips:
        frames, fps, source_size = read_excerpt(path, args.start if args.video else 0, seconds)
        roi = rescale_roi(source_roi, source_size, frames.shape[1:])
        detection_roi = (192, 100, 18, 18) if name == "wrist" else roi
        rows.extend(evaluate(name, frames, fps, roi, band, args.alpha, args.output,
                             detection_roi=detection_roi))
    write_results(args.output, rows)


if __name__ == "__main__":
    main()
