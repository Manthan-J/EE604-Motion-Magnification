"""Run with python demo_auto_frequency.py [--benchmark] [--plot spectrum.png]."""

import argparse
from pathlib import Path

import numpy as np

from src.auto_frequency import FrequencyEstimate, estimate_dominant_frequency, estimate_frequency_from_video


def print_estimate(label: str, result: FrequencyEstimate) -> None:
    """Print a detected rate and cutoffs or the reason to use a manual band."""
    print(label)
    if result.reliable:
        print(f"  Detected frequency {result.peak_hz:.3f} Hz ({result.bpm:.1f} BPM)")
        print(f"  Automatic band {result.low_hz:.3f} to {result.high_hz:.3f} Hz")
    else:
        print(f"  {result.message} Use a manual band or retry with a different clip or ROI.")
    print(f"  Confidence {result.confidence:.2f}")


def save_spectrum(result: FrequencyEstimate, path: Path) -> None:
    """Save the synthetic Welch spectrum with the peak and automatic band."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot(result.frequencies, result.psd, label="Welch PSD")
    if result.reliable:
        ax.axvline(result.peak_hz, color="tab:orange", label="Detected peak")
        ax.axvspan(result.low_hz, result.high_hz, alpha=0.2, label="Automatic band")
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD (signal units squared / Hz)", xlim=(0, 3))
    ax.legend()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Demonstrate synthetic estimation and optionally run a bundled benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", type=Path, help="Save the synthetic PSD plot.")
    parser.add_argument("--benchmark", action="store_true", help="Also estimate from the MIT face clip.")
    args = parser.parse_args()

    fps = 30.0
    time = np.arange(600) / fps
    noise = np.random.default_rng(42).normal(0, 0.8, time.size)
    signal = np.sin(2 * np.pi * 1.2 * time) + noise
    result = estimate_dominant_frequency(signal, fps, 0.7, 2.5)
    print_estimate("Synthetic 1.200 Hz tone with additive noise", result)
    if args.plot:
        save_spectrum(result, args.plot)

    if args.benchmark:
        video = Path(__file__).resolve().parents[1] / "data" / "benchmarks" / "mit_evm" / "face.mp4"
        # Forehead rectangle chosen on the original 528 x 592 first frame.
        detection_roi = (170, 100, 160, 55)
        result = estimate_frequency_from_video(str(video), detection_roi, 0.7, 2.5)
        print_estimate(f"MIT face clip, green-channel ROI {detection_roi} (no reference BPM)", result)


if __name__ == "__main__":
    main()
