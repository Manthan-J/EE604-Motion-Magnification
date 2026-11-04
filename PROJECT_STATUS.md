# EE604 Project Status

This file is the source of truth for verified implementation progress, decisions, blockers, and next steps. Update it after meaningful project work. Record only observed facts; do not mark planned work as complete without evidence.

## Last Updated

- **Date:** November 4, 2026
- **Update:** Synchronized the local project with `origin/main` and prepared a clean single-repository collaboration baseline.

## Current Phase

- Baseline acquisition and compatibility assessment.
- The upstream PyEVM implementation is available locally but has not yet been run end-to-end with the current dependency versions.

## Completed

- Defined the project scope, technical constraints, proposed novelties, deliverables, and team responsibilities in `AGENTS.md`.
- Configured `AGENTS.md` to require reading and maintaining this status file.
- Cloned `https://github.com/flyingzhao/PyEVM.git` into `PyEVM/` at commit `00649cc`.
- Verified that the clone contains `EVM.py` and bundled `baby.mp4` and `guitar.mp4` sample videos.
- Verified that `EVM.py` passes Python syntax compilation using the project virtual environment.
- Initialized the project root as a Git repository with default branch `main`.
- Added `origin` pointing to `https://github.com/Manthan-J/EE604-Motion-Magnification.git`.
- Verified that the remote is reachable and that its `HEAD` points to `main` at commit `7731d16`.
- Processed `PyEVM/guitar.mp4` with the upstream Laplacian-pyramid and Butterworth motion-magnification path using a 0.4--3.0 Hz passband, three pyramid levels, and amplification 20; the generated file is decodable but visually unusable due to severe amplified noise/ringing.
- Created `results/baseline/` for reproducible baseline outputs.
- Moved the failed guitar diagnostic to `results/baseline/guitar_motion_legacy_0.4-3Hz_a20.avi` and documented its parameters and assessment in `results/baseline/README.md`.
- Copied the upstream baby color and motion outputs into `results/baseline/` with provenance and quality labels.
- Confirmed that upstream `baby-result.avi` duplicates `baby-color-result.avi`, so it was not copied into the results directory.
- Downloaded official MIT CSAIL `face.mp4`, `wrist.mp4`, and `subway.mp4` source videos into `data/benchmarks/mit_evm/`.
- Added a benchmark manifest with source attribution, intended test cases, metadata, citation guidance, and SHA-256 checksums.
- Generated and archived a face color baseline using 0.83--1.0 Hz, amplification 100, and three Gaussian-pyramid levels.
- Generated and archived a subway motion baseline using 0.4--3.0 Hz, amplification 20, and three Laplacian-pyramid levels.
- Attempted the full-resolution wrist motion baseline; stopped it after approximately seven minutes without output because of the legacy implementation's memory/runtime behavior.
- Created a documented 320x176 full-duration wrist derivative and successfully generated a half-resolution legacy motion baseline with 0.4--3.0 Hz and amplification 20.
- Attached the local `main` branch to the existing GitHub `origin/main` initial commit without overwriting local project work.
- Extended the repository `.gitignore` so the virtual environment, editor state, downloaded benchmark videos, and generated video outputs remain local rather than entering Git history.
- Converted `PyEVM/` from a nested Git checkout into ordinary attributed reference source and recorded its upstream repository and exact commit in `PyEVM/UPSTREAM.md`.

## In Progress

- Assessing baseline output quality and preparing to refactor the legacy implementation into modular project code.

## Key Decisions

- Use classical, CPU-compatible signal processing rather than deep-learning models.
- Use Laplacian/Gaussian spatial pyramids and temporal Butterworth/IIR bandpass filtering for the baseline.
- Develop automatic ROI-based dominant-frequency detection using FFT/PSD.
- Investigate bilateral filtering for suppressing halo and ringing artifacts.
- Use Streamlit for the interactive interface.

## Verification Evidence

- `AGENTS.md` contains the durable project instructions and the requirement to read and update `PROJECT_STATUS.md`.
- `git -C PyEVM rev-parse --short HEAD` returned `00649cc`.
- `python -m py_compile PyEVM/EVM.py` completed successfully in the project virtual environment.
- Core environment imports succeed: OpenCV 5.0.0, NumPy 2.0.2, SciPy 1.13.1, Streamlit 1.50.0, and Matplotlib 3.9.4.
- `git remote -v` reports the expected GitHub URL for fetch and push.
- `git ls-remote --symref origin HEAD` reports `refs/heads/main` at `7731d16954e8fc1b173586ee23c6a1b4c88ac4c5`.
- The guitar baseline run completed without errors under OpenCV 5.0.0, NumPy 2.0.2, and SciPy 1.13.1.
- `guitar-motion-result.avi` is 432x192 at 30 FPS, contains 300/300 decodable frames, and has a duration of 10.0 seconds.
- A source/output frame comparison shows severe chromatic speckle and ringing in the output. Mean Laplacian variance rises from 5,046.93 in the source to 23,806.28 in the result, indicating amplified high-frequency artifacts rather than a clean magnified motion signal.
- Visual frame assessment shows that `baby_color_upstream_legacy.avi` remains recognizable but contains broad false-colour artifacts across static regions.
- Visual frame assessment shows that `baby_motion_upstream_legacy.avi` is dominated by severe noise and ringing and is not a valid successful output.
- Successfully decoded all frames of the downloaded benchmarks: face 301/301, wrist 894/894, and subway 243/243.
- Verified metadata: face 528x592 at 30 FPS; wrist 640x352 at 30 FPS; subway 640x352 at 29.97 FPS.
- Fully decoded the generated outputs: face 301/301 frames, subway 243/243 frames, and half-resolution wrist 894/894 frames.
- Visual inspection found strong false-color artifacts in face, severe noise/ringing in subway, and heavy block/ringing/color artifacts in wrist; none is a clean successful EVM result.
- `HEAD`, local `main`, and `origin/main` were aligned at the remote initial commit `7731d16` before staging the local project baseline.
- `git status --ignored` confirmed that `venv/`, benchmark MP4 files, and generated AVI outputs are excluded while source and manifest files remain available for tracking.

## Known Problems and Blockers

- The tested guitar motion path runs with current dependencies, but the remaining color-magnification path and other inputs are not yet verified.
- The upstream guitar settings are unsuitable: the 0.4--3.0 Hz band was inherited from the baby example, while guitar motion requires frequency analysis constrained by the video's approximately 15 Hz Nyquist limit.
- The legacy pipeline lacks important safeguards such as zero-phase temporal filtering, transient handling, color-space processing, spatial-wavelength-dependent gain limiting, and controlled clipping; `convertScaleAbs` can further distort negative reconstruction values.
- Full-resolution wrist processing is impractical with the current legacy implementation because it materializes multiple entire-video float64 arrays; only a documented half-resolution output has been completed.

## Next Steps

1. Refactor the baseline into clean, modular code and correct temporal filtering, reconstruction, clipping, and amplification controls.
2. Analyze the guitar ROI spectrum and select a valid passband below Nyquist before regenerating the result.
3. Add ROI-based automatic temporal-frequency tuning.
4. Add artifact suppression and compare it against the baseline.
5. Build the Streamlit interface and produce evaluation material for the report and presentation.

## Important Files

- `AGENTS.md` — stable project context, constraints, and working instructions.
- `PROJECT_STATUS.md` — verified progress, decisions, blockers, and next steps.
- `GEMINI.md` — original project context from which `AGENTS.md` was initialized.
- `PyEVM/EVM.py` — cloned upstream baseline implementation.
- `PyEVM/baby.mp4` and `PyEVM/guitar.mp4` — bundled sample videos for initial verification.
- `results/baseline/README.md` — baseline result manifest with parameters and quality assessments.
- `results/baseline/guitar_motion_legacy_0.4-3Hz_a20.avi` — decodable but visually failed legacy baseline retained for later artifact comparison.
- `results/baseline/baby_color_upstream_legacy.avi` — recognizable but artifact-prone upstream color baseline.
- `results/baseline/baby_motion_upstream_legacy.avi` — visually failed upstream motion baseline.
- `data/benchmarks/mit_evm/README.md` — official-source attribution, benchmark metadata, checksums, and citation guidance.
- `data/benchmarks/mit_evm/face.mp4`, `wrist.mp4`, and `subway.mp4` — verified official MIT CSAIL benchmark inputs.
- `data/derived/wrist_half_resolution.mp4` — documented full-duration half-resolution derivative used for the legacy wrist run.
- `results/baseline/face_color_legacy_0.83-1Hz_a100.avi` — artifact-prone face color baseline.
- `results/baseline/subway_motion_legacy_0.4-3Hz_a20.avi` — visually failed subway motion baseline.
- `results/baseline/wrist_motion_legacy_halfres_0.4-3Hz_a20.avi` — visually failed half-resolution wrist motion baseline.
