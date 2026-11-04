# EE604 Course Project: Eulerian Video Magnification (EVM)

## 1. Project Overview & Deadlines
- **Course & Institution:** EE604, IIT Kanpur (Instructor: Prof. Koteswar Rao J).
- **Core Topic:** Motion Magnification using Eulerian Video Magnification (EVM) with a targeted novelty.
- **Deadline 1 (Write-Up):** November 6, 2026 on HelloIITK. Template: CVPR 2022 Overleaf LaTeX kit.
- **Deadline 2 (Demo & PPT):** November 7–8, 2026 (Live code demo + 8–10 slide presentation).
- **Evaluation Weight:** 15% total (5% Write-up + 5% Code/Demo + 5% Presentation).

## 2. Technical Stack & Implementation Constraints
- **Primary Language:** Python 3.
- **Core Libraries:** OpenCV (`cv2`), NumPy, SciPy (`scipy.signal`, `scipy.fft`), Streamlit (for GUI), Matplotlib.
- **Constraint:** Strictly classical signal processing (Laplacian pyramids + temporal Butterworth/IIR filtering). Do NOT use heavy PyTorch/deep-learning models requiring GPU training.
- **Code Style:** Clean, modular, fully commented with docstrings, and ready to be compiled into the report's code appendix.

## 3. Baseline vs. Proposed Novelty
- **Baseline:** Standard Linear Eulerian Video Magnification (spatial Gaussian/Laplacian pyramid decomposition + temporal bandpass IIR/Butterworth filtering + pixel amplification by factor α).
- **Proposed Novelty 1 (Auto-Tuned Temporal Frequency):** User selects a Region of Interest (ROI) (e.g., wrist or throat), and the pipeline computes temporal FFT / Power Spectral Density (PSD) to automatically identify the dominant oscillation frequency peak, auto-setting the bandpass cutoffs [f_min, f_max] instead of requiring manual tuning.
- **Proposed Novelty 2 (Artifact Suppression):** Edge-preserving bilateral filtering applied across spatial pyramid levels to suppress high-α halo/ringing artifacts around sharp edges.

## 4. Team Division of Labor (4 Group Members)
- **Member 1 (Spatial Pyramids & Literature):** Spatial Gaussian/Laplacian decomposition and bilateral edge-preserving filter; writes Introduction and Literature Review.
- **Member 2 (Temporal Filtering & Auto-Tuning):** Temporal bandpass filtering and ROI FFT peak-frequency auto-tuning module; writes Proposed Method and mathematical justification.
- **Member 3 (Validation, Metrics & Plots):** Testing on benchmark videos (`baby`, `wrist`, `throat`, `guitar`) and custom phone recordings; generates comparison tables, FPS/runtime benchmarks, and space-time (x-t slice) plots; writes Experimental Results.
- **Member 4 (Streamlit UI & Integration):** Builds the interactive Streamlit dashboard (video upload, ROI box selector, α slider, side-by-side playback, real-time spectrum plot); formats CVPR LaTeX write-up, code appendix, and GitHub repo.

## 5. Agent Instructions for Every Session
1. Whenever generating code, make it modular and directly runnable on standard CPU without requiring external weights or GPU hardware.
2. Whenever drafting paper sections, format text and equations specifically for the CVPR 2022 double-column LaTeX format.
3. Always include explanations of "why" a design choice was made to help team members defend their work during the oral exam.
4. At the beginning of every task, read `PROJECT_STATUS.md` to understand the latest verified progress, decisions, blockers, and next steps before making changes.
5. After completing meaningful project work, update `PROJECT_STATUS.md` with what actually changed, relevant verification results, new decisions or blockers, and the next recommended steps. Do not record planned work as completed or include routine command-by-command narration.
