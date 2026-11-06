"""Streamlit interface for the CPU Eulerian video magnification pipeline."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import altair as alt
import cv2
import numpy as np
import streamlit as st

from auto_frequency import estimate_dominant_frequency, extract_roi_signal
from auto_roi import suggest_periodic_roi
from roi_magnification import load_video, magnify_frames


def first_frame(path):
    """Read a frame for the ROI preview without decoding the entire clip."""
    capture = cv2.VideoCapture(str(path))
    try:
        ok, frame = capture.read()
        if not ok:
            raise ValueError("Could not decode the uploaded video.")
        return frame
    finally:
        capture.release()


def find_ffmpeg():
    """Find the system encoder or the existing PsychoPy installation."""
    encoder = shutil.which("ffmpeg")
    if encoder is None:
        bundled = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / (
            "PsychoPy/share/ffpyplayer/ffmpeg/bin/ffmpeg.exe"
        )
        if not bundled.is_file():
            raise OSError("Install FFmpeg with libx264 and add it to PATH to export MP4.")
        encoder = str(bundled)
    return encoder


def encode_original_preview(source, output):
    """Make a browser-compatible copy while keeping the uploaded input for EVM."""
    command = [
        find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if result.returncode:
        raise OSError("FFmpeg could not encode the original preview. " + result.stderr.strip())
    return output.read_bytes()


def encode_mp4(path, original, processed, fps, comparison):
    """Encode browser-compatible H.264 with even dimensions and source timing."""
    height, width = processed.shape[1:3]
    if comparison:
        width *= 2
    command = [
        find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "bgr24", "-video_size", f"{width}x{height}",
        "-framerate", str(fps), "-i", "pipe:0",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ]
    # A file for stderr lets us report encoder failures without filling a pipe.
    with path.with_suffix(".log").open("w+b") as errors:
        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors) as process:
            try:
                for source, result in zip(original, processed):
                    frame = np.concatenate((source, result), axis=1) if comparison else result
                    process.stdin.write(frame.tobytes())
                process.stdin.close()
            except BrokenPipeError:
                pass
            if process.wait():
                errors.seek(0)
                raise OSError("FFmpeg could not encode the preview. " + errors.read().decode(
                    "utf-8", errors="replace"
                ).strip())
    return path.read_bytes()


def expand_roi(box, factor, width, height):
    """Enlarge the analysis box around its center, clipped to the frame."""
    x, y, w, h = box
    pad_x, pad_y = (factor - 1) * w, (factor - 1) * h
    left, top = max(0, x - pad_x // 2), max(0, y - pad_y // 2)
    right = min(width, x + w + (pad_x + 1) // 2)
    bottom = min(height, y + h + (pad_y + 1) // 2)
    return left, top, right - left, bottom - top


def select_roi(frame, data, suffix, upload_key, channel):
    """Return the magnification and frequency-analysis boxes in source pixels."""
    height, width = frame.shape[:2]
    mode = st.radio("ROI selection", ["Automatic ROI", "Manual ROI", "Full frame"], horizontal=True)
    if mode == "Full frame":
        box = (0, 0, width, height)
        return box, box
    if mode == "Automatic ROI":
        key = (upload_key, channel)
        if st.session_state.get("roi_suggestion", (None,))[0] != key:
            try:
                with st.spinner("Searching for localized periodic activity…"), TemporaryDirectory() as directory:
                    path = Path(directory) / f"input{suffix}"
                    path.write_bytes(data)
                    suggestion = suggest_periodic_roi(path, channel=channel)
                st.session_state.roi_suggestion = (key, suggestion)
            except (ValueError, OSError, cv2.error) as error:
                st.error(str(error))
                return None, None
        suggestion = st.session_state.roi_suggestion[1]
        if suggestion is None:
            st.warning("No clear periodic region found. Try Manual ROI or use a longer, steadier clip.")
            return None, None
        detection_roi = suggestion.box
        scale = st.slider("Magnification box scale", 1, 4, 3, format="%dx")
        roi = expand_roi(detection_roi, scale, width, height)
        st.caption(f"Yellow is the {detection_roi[2]} × {detection_roi[3]} pixel frequency patch "
                   f"({suggestion.peak_hz:.2f} Hz). Cyan shows the magnified area when enlarged.")
    else:
        st.caption("Set the horizontal and vertical bounds in original video pixels.")
        left, right = st.slider("Horizontal bounds", 0, width, (0, width))
        top, bottom = st.slider("Vertical bounds", 0, height, (0, height))
        roi = detection_roi = (left, top, right - left, bottom - top)
    preview = frame.copy()
    if roi != detection_roi:
        x, y, w, h = roi
        cv2.rectangle(preview, (x, y), (x + w - 1, y + h - 1), (255, 210, 40), 2)
    x, y, w, h = detection_roi
    if w > 0 and h > 0:
        cv2.rectangle(preview, (x, y), (x + w - 1, y + h - 1), (0, 225, 255), 2)
    st.image(preview, channels="BGR", caption="Regions on the first frame")
    return roi, detection_roi


def process_video(path, output, settings):
    """Estimate the input spectrum, magnify the selected band, and export playback."""
    frames, fps = load_video(path, max_decoded_bytes=192 * 1024**2)
    low, high = settings["manual_band"]
    roi = settings["roi"]
    if not 0 < low < high < fps / 2:
        raise ValueError(f"Require 0 < minimum < maximum < {fps / 2:g} Hz for this video.")

    estimate = None
    search_band = None
    automatic = settings["frequency_mode"] == "Automatic"
    if automatic or settings["spectrum"]:
        search_low, search_high = 0.65, min(3.0, 0.95 * fps / 2)
        if search_low >= search_high:
            search_low, search_high = low, high
        search_band = (search_low, search_high)
        samples = extract_roi_signal(frames, settings.get("detection_roi", roi),
                                     channel=settings["channel"])
        estimate = estimate_dominant_frequency(samples, fps, search_low, search_high)
        if automatic and estimate.reliable:
            low, high = estimate.low_hz, estimate.high_hz

    processed = magnify_frames(
        frames, fps, low, high,
        roi=None if roi == (0, 0, frames.shape[2], frames.shape[1]) else roi,
        amplification=settings["alpha"],
        artifact_suppression=settings["suppression"],
    )
    video = encode_mp4(output, frames, processed, fps, settings["comparison"])
    return {"video": video, "estimate": estimate, "band": (low, high),
            "search_band": search_band}


def display_spectrum(estimate, search_band):
    """Show the full spectrum and distinguish the bins eligible for selection."""
    low, high = search_band
    band = alt.Chart(alt.Data(values=[{"low": low, "high": high}])).mark_rect(
        color="#69b7ef", opacity=0.16
    ).encode(x=alt.X("low:Q", title="Frequency (Hz)"), x2="high:Q")
    spectrum = alt.Chart(alt.Data(values=[
        {"frequency": float(frequency), "psd": float(power)}
        for frequency, power in zip(estimate.frequencies, estimate.psd)
    ])).encode(
        x=alt.X("frequency:Q", title="Frequency (Hz)"),
        y=alt.Y("psd:Q", title="PSD"),
        tooltip=[alt.Tooltip("frequency:Q", title="Frequency (Hz)", format=".3f"),
                 alt.Tooltip("psd:Q", title="PSD", format=".4g")],
    )
    chart = band + spectrum.mark_line()
    if estimate.reliable:
        # Use the original PSD bin even if the estimate was clipped at a boundary.
        peak_bin = float(estimate.frequencies[np.argmin(
            np.abs(estimate.frequencies - estimate.peak_hz)
        )])
        chart += spectrum.transform_filter(alt.datum.frequency == peak_bin).mark_point(
            color="#ffab40", filled=True, size=85
        )
    st.altair_chart(chart)
    st.caption(f"The shaded region is the peak search range ({low:.2f}–{high:.2f} Hz). "
               "Peaks outside it are excluded. An orange dot marks the selected peak when available.")


def display_result(result, settings):
    """Show only results generated with the current inputs and settings."""
    low, high = result["band"]
    st.write(f"Applied passband **{low:.3f}–{high:.3f} Hz**")
    estimate = result["estimate"]
    if estimate is not None:
        search_low, search_high = result["search_band"]
        if estimate.reliable:
            st.write(f"Selected ROI peak within {search_low:.2f}–{search_high:.2f} Hz "
                     f"**{estimate.peak_hz:.3f} Hz** ({estimate.bpm:.1f} cycles/min)")
        elif settings["frequency_mode"] == "Automatic":
            st.warning(f"{estimate.message} Used the manual fallback band.")
        else:
            st.info(estimate.message)
        if settings["spectrum"] and estimate.frequencies.size:
            display_spectrum(estimate, result["search_band"])
    st.caption("Original on the left, magnified on the right" if settings["comparison"]
               else "Magnified output")
    st.video(result["video"], format="video/mp4")
    st.download_button("Download result", result["video"], "motion_magnification.mp4", "video/mp4")


def main():
    """Render controls and retain the latest completed run across UI reruns."""
    st.set_page_config(page_title="Motion Magnification", page_icon="\U0001f50e", layout="wide")
    st.title("Motion Magnification")
    st.caption("Visualise subtle motion through Eulerian video magnification.")
    with st.sidebar:
        st.header("Processing controls")
        alpha = st.slider("Magnification factor (α)", 0, 100, 4)
        mode = st.radio("Frequency mode", ["Manual", "Automatic"])
        if mode == "Automatic":
            st.caption("The manual band is used when the ROI estimate is unreliable.")
        low = st.number_input("Minimum frequency (Hz)", min_value=0.01, value=0.70, step=0.05)
        high = st.number_input("Maximum frequency (Hz)", min_value=0.01, value=1.10, step=0.05)
        channel = st.selectbox("Spectrum channel", ["green", "gray", "mean"])
        suppression = st.checkbox("Artifact suppression")
        spectrum = st.checkbox("Show ROI spectrum", value=True)
        comparison = st.checkbox("Side-by-side comparison", value=True)

    upload = st.file_uploader("Upload video", type=["mp4", "avi", "mov"])
    if upload is None:
        for key in ("source_preview", "roi_suggestion", "result"):
            st.session_state.pop(key, None)
        return

    data = upload.getbuffer()
    upload_key = hashlib.sha256(data).hexdigest()
    suffix = Path(upload.name).suffix.lower()
    if st.session_state.get("source_preview", (None,))[0] != upload_key:
        st.session_state.pop("result", None)
        try:
            with TemporaryDirectory() as directory:
                path = Path(directory) / f"input{suffix}"
                path.write_bytes(data)
                frame = first_frame(path)
                try:
                    with st.spinner("Preparing original video for browser playback…"):
                        preview = encode_original_preview(path, Path(directory) / "preview.mp4")
                    preview_error = None
                except OSError as error:
                    preview = None
                    preview_error = str(error)
                st.session_state.source_preview = (upload_key, frame, preview, preview_error)
        except (ValueError, OSError, cv2.error) as error:
            st.error(str(error))
            return

    _, frame, preview, preview_error = st.session_state.source_preview
    with st.expander("Original video"):
        if preview is not None:
            st.video(preview, format="video/mp4")
        else:
            st.warning(preview_error)
            st.image(frame, channels="BGR", caption="First frame of the upload")
    roi, detection_roi = select_roi(frame, data, suffix, upload_key, channel)
    settings = {
        "roi": roi, "detection_roi": detection_roi,
        "alpha": alpha, "frequency_mode": mode, "manual_band": (low, high),
        "channel": channel, "suppression": suppression, "spectrum": spectrum,
        "comparison": comparison,
    }
    run_key = (upload_key, settings)
    if st.button("Start motion magnification", type="primary", disabled=roi is None) and roi is not None:
        st.session_state.pop("result", None)
        if roi[2] == 0 or roi[3] == 0:
            st.error("The ROI must have positive width and height.")
        else:
            try:
                with st.spinner("Analyzing and processing video on CPU…"), TemporaryDirectory() as directory:
                    path = Path(directory) / f"input{suffix}"
                    path.write_bytes(data)
                    result = process_video(path, Path(directory) / "output.mp4", settings)
                st.session_state.result = (run_key, result)
            except (ValueError, OSError, cv2.error) as error:
                st.error(str(error))

    saved = st.session_state.get("result")
    if saved is not None and saved[0] == run_key and "search_band" in saved[1]:
        display_result(saved[1], settings)
    st.download_button("Save configuration", json.dumps(settings, indent=2),
                       "motion_magnification_config.json", "application/json")


if __name__ == "__main__":
    main()
