"""Suggest an ROI with localized periodic variation using classical DSP."""

from dataclasses import dataclass

import cv2
import numpy as np

from src.auto_frequency import estimate_dominant_frequency


@dataclass(frozen=True)
class RoiSuggestion:
    """A rectangle in source pixels and the frequency that supported it."""

    box: tuple[int, int, int, int]
    peak_hz: float


def _tile_bounds(width, height):
    """Place overlapping square windows at two scales, including image edges."""
    tiles = []
    for fraction in (0.10, 0.20):
        size = min(width, height, max(4, round(fraction * min(width, height))))
        stride = max(1, size // 2)
        lefts = list(range(0, width - size, stride)) + [width - size]
        tops = list(range(0, height - size, stride)) + [height - size]
        tiles.extend((x, y, x + size, y + size) for y in tops for x in lefts)
    return np.array(tiles, dtype=int).T


def suggest_periodic_roi(path, channel="green"):
    """Scan up to 30 seconds for a localized peak between 0.65 and 3 Hz.

    Only per-tile intensity traces are retained. Subtract the median tile
    trace to discount brightness changes that affect most of the image.
    A suggestion describes periodic image activity, not anatomical identity.
    """
    if channel not in ("green", "gray", "mean"):
        raise ValueError("Channel must be green, gray or mean.")
    capture = cv2.VideoCapture(str(path))
    traces = []
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or not np.isfinite(fps) or fps <= 0:
            raise ValueError("Could not read the video or its frame rate for ROI detection.")
        low, high = 0.65, min(3.0, 0.95 * fps / 2)
        if high <= low:
            return None
        for _ in range(round(30 * fps)):
            ok, frame = capture.read()
            if not ok:
                break
            if not traces:
                height, width = frame.shape[:2]
                scale = min(1, 192 / max(width, height))
                scan_width, scan_height = max(1, round(width * scale)), max(1, round(height * scale))
                if min(scan_width, scan_height) < 4:
                    return None
                left, top, right, bottom = _tile_bounds(scan_width, scan_height)
                area = (right - left) * (bottom - top)
            small = cv2.resize(frame, (scan_width, scan_height), interpolation=cv2.INTER_AREA)
            if channel == "green":
                intensity = small[..., 1]
            elif channel == "gray":
                intensity = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            else:
                intensity = small.mean(axis=2, dtype=np.float32)
            integral = cv2.integral(intensity, sdepth=cv2.CV_64F)
            traces.append((integral[bottom, right] - integral[top, right]
                           - integral[bottom, left] + integral[top, left]) / area)
    finally:
        capture.release()
    if len(traces) / fps < 3 / low:
        return None

    samples = np.asarray(traces)
    samples -= np.median(samples, axis=1, keepdims=True)
    thirds = np.array_split(samples, 3) if len(samples) / fps >= 9 / low else ()
    best_score = 0.0
    suggestion = None
    for index, trace in enumerate(samples.T):
        estimate = estimate_dominant_frequency(trace, fps, low, high, min_confidence=8.0)
        if not estimate.reliable:
            continue
        spacing = estimate.frequencies[1]
        peak_bins = np.abs(estimate.frequencies - estimate.peak_hz) <= 1.5 * spacing
        peak_power = estimate.psd[peak_bins].sum()
        if np.sqrt(2 * spacing * peak_power) < 0.15:
            continue
        # Favor energy concentrated in a narrow peak over broadband movement.
        score = peak_power * (peak_power / estimate.psd.sum()) ** 2
        if score <= best_score:
            continue
        if thirds:
            peaks = [
                estimate_dominant_frequency(part[:, index], fps, low, high,
                                            min_confidence=8.0).peak_hz
                for part in thirds
            ]
            # Require a similar peak in two windows to reject isolated motion.
            if sum(peak is not None and abs(peak - estimate.peak_hz) <= 0.18 for peak in peaks) < 2:
                continue
        best_score = score
        x, x2 = (round(bound[index] * width / scan_width) for bound in (left, right))
        y, y2 = (round(bound[index] * height / scan_height) for bound in (top, bottom))
        suggestion = RoiSuggestion((x, y, x2 - x, y2 - y), estimate.peak_hz)
    return suggestion
