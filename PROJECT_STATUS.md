# EE604 Project Status

This file is the source of truth for verified implementation progress, decisions, blockers, and next steps. Update it after meaningful project work. Record only observed facts; do not mark planned work as complete without evidence.

## Last Updated

- **Date:** November 6, 2026
- **Update:** Integrated the shared spatial code, added reproducible ablations and plots, and brought the CVPR write-up in line with the app.

## Current Phase

- Integrated CPU pipeline and demo verified on bundled inputs. Report sources and generated measurements are ready for the CVPR 2022 author kit.

## Completed

- Added `auto_roi.py` and a default Automatic ROI mode alongside Manual ROI and Full frame. It scans up to 30 seconds, subtracts the median tile trace to discount global flicker, and ranks local periodic signals between 0.65 and 3 Hz. For sufficiently long clips, it checks whether the peak recurs across time windows. The box is an activity-based suggestion and can be overridden manually. ROI detection and passband selection are separate controls.

- Added the integrated root `app2.py` and brought the submitted `src/spatial.py` into the local working tree. The UI exposes a pixel-coordinate ROI with an overlay, manual and automatic bands, ROI PSD, estimated oscillation rate, suppression toggle, and synchronized original/processed MP4 playback. The UI decodes at most 192 MiB of raw frames per job and exports video without audio using FFmpeg with libx264. The earlier UI prototype remains in the ignored review folder.
- Integrated the submitted bilateral operation on each signed, temporally filtered luminance detail band in the optional frame-array path. Scale the color sigma by gain so it represents the same intensity tolerance after amplification. The final ROI mask still gates the reconstructed adjustment, and the default suppression-off path preserves baseline behavior.

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
- Added the MIT `face`, `subway`, and `wrist` benchmarks, the derived half-resolution wrist input, and PyEVM's `baby` and `guitar` inputs to Git for reproducible teammate testing.
- Created editable Word and PDF team briefs under `docs/` covering the recommended novelty scope, four-member allocation, ablation matrix, evaluation requirements, and deadline safeguards.
- Added `auto_frequency.py` for green, grayscale and mean ROI extraction, Welch PSD, prominence-based peak selection, BPM conversion and guarded automatic bandpass cutoffs. The video wrapper retains only one scalar per decoded frame.
- Added `tests/test_auto_frequency.py` for deterministic frequency, fallback, validation and ROI extraction tests. Added `demo_auto_frequency.py` for the noisy synthetic demo, optional PSD plotting and the bundled MIT face benchmark.
- Renamed the submitted `ROI.py` to `roi_magnification.py` and verified the SHA-256 stayed identical. Tested the callable pipeline with scripted ROI selection. The interactive OpenCV window was not exercised.
- Fixed the renamed prototype. The frame-array API and CLI now accept an explicit ROI, the CLI can also select one interactively, and cancellation skips processing. The lossless AVI writer preserves fractional FPS and pads odd dimensions at the right/bottom instead of losing pixels.
- Added `--auto-frequency` to the ROI CLI. The box from OpenCV or `--roi` is reused for frequency estimation on the original decoded frames and for the magnification mask. A reliable estimate supplies the filter cutoffs. An unreliable result prints its reason and falls back to the manual band.

## In Progress

- Assessing baseline output quality and preparing to refactor the legacy implementation into modular project code.

## Key Decisions

- Use classical, CPU-compatible signal processing rather than deep-learning models.
- Use Laplacian/Gaussian spatial pyramids and temporal Butterworth/IIR bandpass filtering for the baseline.
- Develop automatic ROI-based dominant-frequency detection using FFT/PSD.
- Investigate bilateral filtering for suppressing halo and ringing artifacts.
- Use Streamlit for the interactive interface.
- Pass `detection_roi` as an original-frame `(x, y, width, height)` tuple with top-left origin, independent of the magnification ROI. The frame-array API expects OpenCV BGR frames in `(time, height, width, 3)` order.
- Treat invalid settings and malformed inputs as `ValueError`. Treat unusable signals or spectral estimates as `reliable=False`, with an explanatory message and the PSD when available. Cutoffs and BPM are populated only when the estimate is reliable.
- Use the ratio of peak PSD to median in-band PSD as a spectral-contrast heuristic. Choose Welch segments long enough to resolve the search band when the clip permits, and cap the filter high cutoff at 95% of Nyquist.
- In the ROI motion path, apply masks matched to the Laplacian detail scales, then feather the reconstructed residual inward to prevent leakage. Filter luminance with zero-phase Butterworth sections to prevent phase lag and a static-scene startup pulse. Apply one signed adjustment to all channels within their shared available range to preserve color differences. Use α=4 by default to reduce high-gain edge artifacts.

## Verification Evidence

- The ROI pipeline now calls `src/spatial.py` for signed decomposition, detail reconstruction and bilateral filtering. It keeps the existing detail order, excludes the unfiltered Gaussian base, and retains the final inward feather. All 24 local tests passed after the integration. A Streamlit AppTest ran automatic ROI, 0.900 Hz selection, the PSD display and per-level suppression, then decoded 894 side-by-side frames at 640×176 and 30 FPS.
- `benchmark_evm.py` ran six matched configurations on synthetic, wrist, baby and guitar inputs and wrote CSV, processing FPS, LaTeX table rows and horizontal space-time plots to `results/validation/`. With α=4, wrist outside-ROI RMS fell from 2.12 levels to zero when localization was enabled. At fixed wrist ROI and band, the bilateral toggle reduced target gain from 2.41× to 2.30×. On synthetic motion it increased clean-reference RMSE from 4.93 to 6.45 levels at the same ROI and band. The full wrist configuration processed 76.7 FPS in one run excluding decode and encode.
- The custom input path processed a 450-frame private wrist excerpt and selected 1.598 Hz. The user-reported 88 BPM was not synchronized to the excerpt. No throat clip was available. The report now documents these limits and includes the real source paths in its appendix. The local machine has no LaTeX compiler, so PDF rendering still needs to be checked in the CVPR author kit.

- The release audit passed all 24 unit tests. A Streamlit AppTest with a simulated wrist upload exercised automatic ROI, 0.900 Hz selection, the updated spectrum, per-level suppression, and MP4 export. The side-by-side export decoded to all 894 frames at 640×176 and 30 FPS. This test exercised the Streamlit controls and file export without browser playback.
- GitHub `main` was at `d97d926` and already contained the spatial teammate branch. The only change unique to `Motion_Magnification_web` was its prototype `app2.py`. The local pipeline imports the submitted bilateral filter, while it uses its own detail-only decomposition and reconstruction. The report still describes a Gaussian ROI mask and a shared detection and magnification box, whereas the implementation uses an inward linear feather and can use separate boxes. Experimental tables, runtime, space-time figures and appendix paths are incomplete. The conditional push was withheld. Before publishing, reconcile the report with the implemented pipeline, finish the matched validation, and integrate against current GitHub `main`.

- With the half-resolution wrist benchmark and frequency patch `(192, 100, 18, 18)`, the full ROI spectrum reached its maximum at 0.100 Hz. The detector selected 0.900 Hz within its 0.65–3.00 Hz search range and applied 0.70–1.10 Hz in automatic mode. Verified that the chart specification shades the actual search range and marks the 0.900 Hz bin. All 24 unit tests passed.

- The automatic ROI now uses the detected patch for the frequency estimate and a centered, frame-clipped 1×–4× box for magnification, with 3× as the default. Manual and full-frame selection use the same region for both tasks. The Streamlit test confirmed the wrist frequency patch stayed at `(192, 100, 18, 18)` and 0.900 Hz while the default magnification box expanded to `(174, 82, 54, 54)`. On the first 180 wrist frames at α=4 and 0.70–1.10 Hz, the 1× and 3× boxes changed a mean of 80.9 and 1362.0 pixels per frame respectively, all within their respective magnification boxes before encoding. All 24 unit tests passed. The expanded region is a geometric crop, and its anatomy and visual quality depend on the clip.

- The synthetic ROI probe rejected uniform 1.5 Hz flicker and recovered a localized 1.2 Hz patch over that flicker. The wrist benchmark returned `(192, 100, 18, 18)` and 0.900 Hz. A Streamlit AppTest verified the suggested box flowed into automatic frequency estimation and synchronized output with suppression enabled, and that switching to Manual ROI hid the stale result. All 24 existing unit tests passed. The integrated automatic ROI mode has not been exercised in the user's browser.

- The half-resolution wrist upload uses MPEG-4 Part 2 (`mp4v`), which caused an unplayable original preview in the user's browser. The app now serves a cached H.264/yuv420p MP4 preview with AAC audio when present. ROI and EVM processing still use the upload. Streamlit AppTest confirmed that the video element receives the converted preview and reuses it after settings changes. The converted wrist preview decoded to all 894 frames at 30 FPS. All 24 unit tests passed. Browser playback of the converted preview remains to be checked.

- All 24 unit tests passed, including outside-ROI and color-difference checks with suppression off and on. A Streamlit AppTest with simulated wrist upload and manual bounds `(150, 72, 72, 60)` exercised automatic frequency, the PSD display, suppression enabled, and side-by-side H.264 output. It detected 0.900 Hz and applied 0.700–1.100 Hz. All 894 output frames decoded at 30 FPS at 640×176. A reversed band showed a validation error and cleared prior playback. A constant AVI exercised automatic fallback and the manual export path. Browser upload and playback of the integrated app still need a manual check.

- Generated matched suppression-off/on comparisons in `results/artifact_suppression_review/` using `temp/compare_artifact_suppression.py`. Applied the submitted default bilateral filter after reconstruction to full frames normalized to 0–1. The deterministic synthetic edge test reduced flat-region noise SD from 3.55 to 1.02 and near-edge ripple RMS from 4.94 to 3.44 intensity levels (0–255). Mean edge contrast stayed near 81.7 levels. The same filter defaults had effectively no effect on the 0–255 float input.
- Compared the first 300 frames at 30 FPS of the wrist (ROI `(145, 37, 125, 89)`, 0.8–2.0 Hz) and baby (ROI `(173, 104, 128, 79)`, 0.4–1.0 Hz) samples at α=4 and α=20. With α=20, the filter changed the ROI by a mean of 2.13 intensity levels on wrist and 2.36 on baby. Stills show less fine grain on the baby's clothing and persistent speckle on the wrist. The full-frame filter changed about 78% (wrist) and 86% (baby) of outside-ROI pixels at both gains, measured before encoding. Both α=20 comparison MP4s decoded to 300 frames at 30 FPS. Real clips have no artifact-free magnified reference, so motion preservation and artifact removal on real video were not established quantitatively.

- GitHub `main` at `d97d926` includes `feature/artifact-suppression` at `6f53ec3`. `Motion_Magnification_web` at `97bec86` adds `app2.py` and is one commit ahead and two behind `main`. The reviewed source files were staged as local copies in ignored `temp/teammate-review/` for testing.
- The local 24 unit tests passed. The three teammate spatial scripts ran, but they duplicate the implementation and exercise synthetic frames. A separate check importing `src/spatial.py` reconstructed even and odd BGR frames exactly for the tested inputs and preserved negative detail coefficients. On a normalized synthetic noisy step, the bilateral filter reduced flat-region noise standard deviation from 0.0101 to 0.0028 while retaining the step contrast. The same defaults left the 0–255 version effectively unchanged. The high-gain and large-motion example PNGs had identical saturated pixel counts with the toggle off and on (100 and 1,000 respectively).
- As a compatibility probe, applied the submitted filter to a normalized full frame from a 180-frame wrist run with `(150, 72, 72, 60)`, 0.7–1.1 Hz, and α=20. It changed 41,145 pixels outside the ROI on the sampled frame. The submission filters a reconstructed frame; the planned method specifies filtering across pyramid levels. Compare matched real-video outputs after integration and check both residual artifacts and retained target motion.
- Streamlit `AppTest` confirmed startup, video preview with a simulated upload, and rejection of reversed manual cutoffs. Valid manual processing, automatic processing, and ROI selection displayed placeholder messages. Browser playback and upload were not tested. `app2.py` has no call into the ROI pipeline, frequency estimator, or suppression module.

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
- The six shared MP4 inputs total approximately 11.8 MiB; generated AVI outputs remain ignored and untracked.
- `.\venv\Scripts\python.exe -m py_compile auto_frequency.py demo_auto_frequency.py tests/test_auto_frequency.py` passed in the project Python 3.9 environment.
- `.\venv\Scripts\python.exe -m unittest discover -s tests -v` passed all 15 tests.
- `.\venv\Scripts\python.exe demo_auto_frequency.py --benchmark --plot temp/ee604_auto_frequency_psd.png` detected 1.200 Hz (72.0 BPM), selected 1.000–1.400 Hz, and reported confidence 47.71 on the noisy synthetic signal. The PSD plot was generated and checked.
- The same demo decoded the original 528×592 MIT face clip with the green-channel forehead ROI `(170, 100, 160, 55)` and 0.7–2.5 Hz search limits. It detected a 0.900 Hz peak (54.0 cycles/min), selected 0.700–1.100 Hz, and reported confidence 927.86. The clip provides no reference BPM, so this is a pipeline smoke test.

- ROI review outputs are under `results/roi_review/`. The original AVI results and comparison MP4s each decoded to 300 frames at 30 FPS. All runs used three Laplacian detail levels. Boxes are in processed-frame `(x, y, width, height)` coordinates.
  - Synthetic two-edge video, 176×96, box `(26, 19, 57, 43)`, 0.8–1.6 Hz, α=4. After excluding the first five seconds, the pre-encode 1.2 Hz pixel amplitude at the target edge increased 3.94×. The distant control was unchanged. A point outside the box increased 2.24×, and 266 pixels outside the box changed by more than one intensity level.
  - First 300 frames of `PyEVM/baby.mp4`, resized to 480×272, box `(173, 104, 128, 79)`, 0.4–1.0 Hz, α=20. The result shows ringing and false color around the clothing seams.
  - First 300 frames of `data/derived/wrist_half_resolution.mp4`, 320×176, box `(145, 37, 125, 89)`, 0.8–2.0 Hz, α=20. The result shows conspicuous colored speckle and edge artifacts.
- ROI diagnostics reproduced an OpenCV shape error on a 97×65 frame and a missing-file crash when running the script from the repository root. A 29.97 FPS input was interpreted as 29 FPS for filtering while the writer fixes output at 30 FPS. The 0.8–1.6 Hz filter responded to a static coefficient of 100 with a startup transient of magnitude 23.67 before amplification. All 15 existing frequency-estimation tests still pass.
- The corrected outputs are under `results/roi_fixed/`. Reran the same three inputs, boxes and passbands. All five lossless AVIs and comparison MP4s decoded to 300 frames at 30 FPS. Decoded AVIs preserved every pixel outside the box exactly and preserved BGR channel differences across the frame. Synthetic in-box 1.2 Hz amplitude grew 3.92× at α=4; the point just outside and the distant control both stayed at 1.00×. Baby and wrist were rerun at α=4 and α=20. Frame inspection showed much stronger edge ringing and grain at α=20.
- All 22 unit tests pass, including odd pyramid sizes and signed details, a constant-signal transient check, small ROI support, outside-ROI preservation, 29.97 FPS lossless round-trip with odd-size padding, cancellation, and invalid passband. The CLI produced an output with an explicit ROI and reported a clear missing-file error. The interactive window itself remains untested.
- Personal recordings were tested at native resolution on steadier excerpts with three levels and α=4. Face `16–30 s`, forehead box `(120, 330, 155, 105)`, 0.70–1.05 Hz, 419 frames. Wrist `5–20 s`, inner-wrist box `(226, 472, 129, 166)`, 0.70–1.50 Hz, 449 frames. The wrist used a broader band because the diagnostic green-channel peaks varied across subsegments. All four MP4s under `results/personal_recordings/` decoded to their expected frame counts and approximately 29.97 FPS. Pixels outside each box were identical before MP4 encoding. Mean absolute in-box change was 3.15 and 3.71 intensity levels (on a 0–255 scale), respectively. Frame inspection showed stronger eyebrow edges on the face and stronger crease detail and grain on the wrist. These clips verify localized amplification. They have no reference signal for pulse validation.
- Pulse diagnostic on the original excerpts used mean green and a 1.6 s POS RGB projection, Welch PSD over 0.65–3.0 Hz, the whole excerpts and their halves, and off-skin background controls. The face forehead green peak near 0.70 Hz also appeared in the whole-excerpt background spectrum, and the cheek peaks disagreed. The wrist green peak moved from about 1.20 to 0.80 Hz between halves, with peaks at those frequencies in the corresponding background windows. POS did not produce a consistent peak across skin patches and halves on either clip. No BPM was reported. For validation, collect a simultaneous reference pulse on a repeat recording.
- With the original personal-recording ROIs and the integrated default green-channel search (0.65–3.00 Hz), the face excerpt at 16–30 s returned 0.799 Hz (48.0 cycles/min) and the wrist excerpt at 5–20 s returned 1.598 Hz (95.9 cycles/min). The user's reference was 88 BPM. The two face halves returned about 43 and 51 cycles/min, and the two wrist halves about 72 and 40 cycles/min. The wrist background also contained a peak near 96 cycles/min. Both outputs passed the estimator's spectral-contrast heuristic, but neither was a reliable pulse measurement against the reported reference.
- Bundled MIT wrist benchmark: decoded all 894 original frames at 30 FPS. After screening wrist tiles, analyzed mean green with a linearly detrended Hann periodogram over 0.55–2.50 Hz. The original-frame boxes `(360, 208, 32, 32)` and `(344, 176, 32, 32)` peaked at 0.927 and 0.934 Hz (55.6 and 56.0 BPM). Both returned approximately 54 BPM in the first half and 57 BPM in the second half. Spectral power near the wrist peak was about 88 times higher in the first wrist box than in the tabletop control `(10, 270, 100, 50)`. Figure 7 of the [MIT EVM paper](https://people.csail.mit.edu/mrub/papers/vidmag.pdf) reports 0.88 Hz (53 BPM) for this clip. This is an exploratory benchmark estimate with data-selected patches.
- The integrated CLI ran on `data/derived/wrist_half_resolution.mp4` with `--roi 180 104 16 16 --auto-frequency`. Welch selected 0.900 Hz (54.0 cycles/min) and set the passband to 0.700–1.100 Hz. All 894 frames of `results/roi_auto/wrist_auto.avi` decoded at 30 FPS, and all changed pixels were inside the box. All 24 unit tests passed, including same-box selection with a competing outside tone and fallback on a constant ROI. The interactive selection path was exercised with a simulated box.
- Transcoded the lossless wrist AVI to `results/roi_auto/wrist_auto.mp4` with H.264 and verified that all 894 frames decode at 30 FPS. The AVI is the source for pixel-exact checks and the MP4 is for playback.
- The initial wrist ROI was only 16×16 pixels and its mean absolute in-box change was 0.57 on a 0–255 intensity scale. Reran the integrated CLI with `--roi 150 72 72 60 --alpha 10 --auto-frequency`. It again detected 0.900 Hz and selected 0.700–1.100 Hz. The new lossless `wrist_auto_demo.avi` averaged 3.56 levels of change within the larger ROI and preserved the outside pixels exactly. The H.264 `wrist_auto_zoom_comparison.mp4` shows the original and output with a 5× crop. All 894 comparison frames decoded at 30 FPS. The higher gain makes local changes easier to see and accentuates some grain.

## Known Problems and Blockers

- The tested guitar motion path runs with current dependencies, but the remaining color-magnification path and other inputs are not yet verified.
- The upstream guitar settings are unsuitable: the 0.4--3.0 Hz band was inherited from the baby example, while guitar motion requires frequency analysis constrained by the video's approximately 15 Hz Nyquist limit.
- The legacy pipeline lacks important safeguards such as zero-phase temporal filtering, transient handling, color-space processing, spatial-wavelength-dependent gain limiting, and controlled clipping; `convertScaleAbs` can further distort negative reconstruction values.
- Full-resolution wrist processing is impractical with the current legacy implementation because it materializes multiple entire-video float64 arrays; only a documented half-resolution output has been completed.
- Short clips and narrow search ranges may lack enough cycles or PSD bins. The estimator assumes uniform sample spacing and uses reported FPS for decoded video. Flicker, camera motion, harmonics or poor ROI placement can produce a prominent unrelated peak. The BPM output is for the course demo.

- High ROI gain still amplifies in-band noise and produces edge artifacts. The motion path adjusts luminance only and its shared channel headroom can limit changes at saturated pixels. The earlier comparison measured full-frame post-filtering. Artifact reduction and target motion retention with the integrated pyramid-level variant still need a matched real-video ablation.

## Next Steps

1. Build the report in the CVPR 2022 Overleaf kit and check pagination, tables, figures and appendix listings.
2. Run the custom validation path on a throat clip when one is available.
3. Check interactive upload and synchronized playback on the demo machine.

## Important Files

- `AGENTS.md` — stable project context, constraints, and working instructions.
- `PROJECT_STATUS.md` — verified progress, decisions, blockers, and next steps.
- `GEMINI.md` — original project context from which `AGENTS.md` was initialized.
- `PyEVM/EVM.py` — cloned upstream baseline implementation.
- `roi_magnification.py` — corrected standalone ROI-guided motion magnification module and CLI.
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
