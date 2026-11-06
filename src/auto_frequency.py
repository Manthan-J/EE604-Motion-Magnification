"""ROI-based frequency detection for Eulerian video magnification."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from numbers import Integral

import cv2
import numpy as np
from scipy.signal import detrend, find_peaks, welch


@dataclass
class FrequencyEstimate:
    """A frequency estimate and its diagnostic spectrum.

    Unreliable results omit the peak, BPM and cutoffs. The spectrum is retained
    when available, and confidence is a PSD ratio, expressed on a linear scale.
    """

    peak_hz: float | None
    bpm: float | None
    low_hz: float | None
    high_hz: float | None
    confidence: float
    reliable: bool
    frequencies: np.ndarray
    psd: np.ndarray
    message: str


def extract_roi_signal(
    frames: np.ndarray,
    roi: tuple[int, int, int, int],
    channel: str = "green",
) -> np.ndarray:
    """Return one spatially averaged intensity per OpenCV BGR frame.

    Frames have shape (time, height, width, 3). The detection ROI is
    (x, y, width, height) in original-frame pixels with a top-left origin.
    The green channel can pick up blood-volume changes because hemoglobin
    absorbs green light strongly (Verkruysse et al., 2008, Optics Express).
    Grayscale uses weighted brightness, useful when motion moves a contrast
    edge across the ROI. The mean channel weights all three colors equally.
    Invalid frame shapes, channels and ROIs raise ValueError.
    """
    frames = np.asarray(frames)
    if frames.ndim != 4 or frames.shape[-1] != 3 or frames.size == 0:
        raise ValueError("Expected nonempty BGR frames with shape (time, height, width, 3).")
    if not np.issubdtype(frames.dtype, np.number) or np.iscomplexobj(frames):
        raise ValueError("Frame intensities must be real numbers.")
    if channel not in ("green", "gray", "mean"):
        raise ValueError("Channel must be green, gray or mean.")
    if not isinstance(roi, tuple) or len(roi) != 4 or any(
        not isinstance(value, Integral) or isinstance(value, bool) for value in roi
    ):
        raise ValueError("ROI must be a tuple of four integer pixel coordinates.")

    x, y, width, height = map(int, roi)
    _, frame_height, frame_width, _ = frames.shape
    if (
        x < 0 or y < 0 or width <= 0 or height <= 0
        or x + width > frame_width or y + height > frame_height
    ):
        raise ValueError("ROI must have positive dimensions and fit inside the original frame.")

    pixels = frames[:, y:y + height, x:x + width]
    if channel == "green":
        return pixels[..., 1].mean(axis=(1, 2), dtype=np.float64)
    if channel == "gray":
        # Grayscale conversion and spatial averaging commute in floating point.
        bgr_means = pixels.mean(axis=(1, 2), dtype=np.float64)
        return bgr_means @ np.array([0.114, 0.587, 0.299])
    return pixels.mean(axis=(1, 2, 3), dtype=np.float64)


def estimate_dominant_frequency(
    signal: np.ndarray,
    fps: float,
    min_hz: float,
    max_hz: float,
    band_half_width_hz: float = 0.2,
    min_confidence: float = 3.0,
) -> FrequencyEstimate:
    """Estimate a periodic component of a uniformly sampled ROI signal.

    Welch averages overlapping Hann-windowed periodograms to reduce variance
    compared with a single FFT. Linear detrending suppresses slow drift. Welch
    segments target at least ten seconds, three periods at the lower search
    bound and five frequency steps across the band, subject to clip length.
    The bin spacing is fps / segment length. Short recordings may provide only
    one segment, too few in-band bins, or too few cycles to support an estimate.

    Rank local maxima in the search band by their prominence in the full
    spectrum. Neighboring bins outside the band help distinguish peaks at a
    band boundary from a spectral slope. Confidence is peak PSD divided by
    median in-band PSD, with a numerical floor for near-zero denominators.
    This is a heuristic for spectral contrast. Flicker, camera motion or a
    misplaced ROI can yield a strong unrelated peak. Weak periodicity can
    yield an unreliable result. BPM is the oscillation rate for a course demo.

    The search band must be positive and strictly below Nyquist (fps / 2),
    where aliasing makes higher frequencies ambiguous. Place cutoffs one half
    width on either side of the peak and clip to the search limits and 95% of
    Nyquist. Fall back if the clipped band cannot contain the peak.

    Invalid settings and empty or malformed signals raise ValueError. Signals
    with NaN or infinity return an unreliable result to preserve sample timing
    and avoid introducing artificial periodicity by filling missing data.
    """
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be positive and finite.")
    nyquist = fps / 2.0
    if not 0 < min_hz < max_hz < nyquist:
        raise ValueError("Frequency limits must satisfy 0 < min_hz < max_hz < Nyquist.")
    if not np.isfinite(band_half_width_hz) or band_half_width_hz <= 0:
        raise ValueError("Band half-width must be positive and finite.")
    if not np.isfinite(min_confidence) or min_confidence <= 0:
        raise ValueError("Minimum confidence must be positive and finite.")

    samples = np.asarray(signal)
    if samples.ndim != 1 or samples.size == 0:
        raise ValueError("Expected a nonempty one-dimensional signal.")
    if not np.issubdtype(samples.dtype, np.number) or np.iscomplexobj(samples):
        raise ValueError("Signal samples must be real numbers.")
    samples = samples.astype(np.float64, copy=False)
    frequencies = np.empty(0)
    psd = np.empty(0)

    def fallback(message: str, confidence: float = 0.0) -> FrequencyEstimate:
        return FrequencyEstimate(
            None, None, None, None, confidence, False, frequencies, psd, message
        )

    if not np.all(np.isfinite(samples)):
        return fallback("ROI signal contains NaN or infinite samples.")
    if samples.size < 3:
        return fallback("Clip is too short to estimate a frequency.")

    target_seconds = max(10.0, 3.0 / min_hz, 5.0 / (max_hz - min_hz))
    segment_length = ceil(min(samples.size, fps * target_seconds))
    centered = detrend(samples, type="linear")
    # Treat regression residue at floating-point precision as zero variation.
    roundoff = 8.0 * np.finfo(float).eps * np.max(np.abs(samples))
    has_variation = np.max(np.abs(centered)) > roundoff
    if not has_variation:
        centered.fill(0)
    frequencies, psd = welch(
        centered, fs=fps, window="hann", nperseg=segment_length, detrend="constant"
    )
    if not np.all(np.isfinite(psd)):
        frequencies, psd = np.empty(0), np.empty(0)
        return fallback("Could not compute a finite ROI spectrum.")
    if not has_variation:
        return fallback("ROI signal has no variation after detrending.")

    # Allow one floating-point step at each inclusive search boundary.
    in_band = (
        (frequencies > 0)
        & (frequencies >= np.nextafter(min_hz, -np.inf))
        & (frequencies <= np.nextafter(max_hz, np.inf))
    )
    if samples.size / fps < 3.0 / min_hz or np.count_nonzero(in_band) < 5:
        return fallback("Clip is too short to resolve the search band. Try a longer clip.")

    peaks, properties = find_peaks(psd, prominence=(None, None))
    valid_peaks = in_band[peaks]
    if not np.any(valid_peaks):
        return fallback("No local spectral peak in the search band.")
    peak_index = peaks[valid_peaks][np.argmax(properties["prominences"][valid_peaks])]
    peak_hz = float(np.clip(frequencies[peak_index], min_hz, max_hz))
    peak_power = float(psd[peak_index])
    float_info = np.finfo(float)
    noise_floor = max(
        float(np.median(psd[in_band])), float_info.eps * peak_power, float_info.tiny
    )
    confidence = peak_power / noise_floor
    if confidence < min_confidence:
        return fallback(
            f"Peak confidence {confidence:.2f} is below the threshold {min_confidence:g}.",
            confidence,
        )

    low_hz = max(min_hz, peak_hz - band_half_width_hz)
    high_hz = min(max_hz, peak_hz + band_half_width_hz, 0.95 * nyquist)
    if low_hz >= high_hz or not low_hz <= peak_hz <= high_hz:
        return fallback("The Nyquist safety margin leaves no usable band around the peak.", confidence)

    return FrequencyEstimate(
        peak_hz, 60.0 * peak_hz, low_hz, high_hz, confidence, True,
        frequencies, psd, "Dominant frequency detected.",
    )


def estimate_frequency_from_video(
    video_path: str,
    roi: tuple[int, int, int, int],
    min_hz: float,
    max_hz: float,
    channel: str = "green",
) -> FrequencyEstimate:
    """Decode a video using OpenCV and estimate frequency from a fixed detection ROI.

    Retain only one scalar per frame to keep memory use low. Use the video's
    reported FPS, which assumes constant frame spacing. Unreadable videos and
    invalid settings raise ValueError.
    """
    capture = cv2.VideoCapture(str(video_path))
    samples = []
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            samples.append(extract_roi_signal(frame[None], roi, channel)[0])
    finally:
        capture.release()
    if not samples:
        raise ValueError(f"Video has no decodable frames: {video_path}")
    return estimate_dominant_frequency(np.asarray(samples), fps, min_hz, max_hz)
