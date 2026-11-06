# Baseline Results

This directory stores outputs produced by the classical baseline pipeline. Keep
the input name, temporal passband, amplification, and implementation variant in
each filename or its accompanying notes so future comparisons are reproducible.

## Current Results

### `baby_color_upstream_legacy.avi`

- Source: bundled upstream `data/pyevm/baby.mp4`
- Provenance: pre-generated file supplied by upstream commit `00649cc`; not
  generated or parameter-verified in the current environment
- Output: 960x544, 30 FPS, 301 frames, approximately 10.03 seconds
- Assessment: **recognizable but artifact-prone legacy baseline**. The baby and
  scene remain clear, but broad false-colour blotches also appear across static
  bedding and crib regions. Retain it for visual comparison, not as a clean or
  quantitatively validated result.

### `baby_motion_upstream_legacy.avi`

- Source: bundled upstream `data/pyevm/baby.mp4`
- Provenance: pre-generated file supplied by upstream commit `00649cc`; not
  generated or parameter-verified in the current environment
- Output: 960x544, 30 FPS, 301 frames, approximately 10.03 seconds
- Assessment: **failed visual-quality baseline**. Severe noise and ringing cover
  most of the frame, so it is not a valid successful motion-magnification result.

The upstream `baby-result.avi` is not copied here because its SHA-256 hash is
identical to `baby-color-result.avi`.

### `guitar_motion_legacy_0.4-3Hz_a20.avi`

- Source: `data/pyevm/guitar.mp4`
- Implementation: unmodified `data/pyevm/EVM.py` motion path at upstream commit `00649cc`
- Temporal filter: fifth-order causal Butterworth bandpass (`scipy.signal.lfilter`)
- Passband: 0.4--3.0 Hz
- Amplification: 20
- Pyramid levels: 3
- Output: 432x192, 30 FPS, 300 frames, 10.0 seconds
- Assessment: **failed visual-quality baseline**. The file is fully decodable,
  but it contains severe amplified noise and ringing and should not be presented
  as a successful EVM result.

This failed run is retained deliberately as a reference for artifact comparison
after temporal filtering, gain control, reconstruction, and clipping are fixed.

### `face_color_legacy_0.83-1Hz_a100.avi`

- Source: `data/benchmarks/mit_evm/face.mp4`
- Implementation: unmodified `data/pyevm/EVM.py` color path at upstream commit `00649cc`
- Temporal filter: ideal FFT bandpass
- Passband: 0.83--1.0 Hz
- Amplification: 100
- Pyramid levels: 3
- Output: 528x592, 30 FPS, 301 frames
- Assessment: **recognizable but heavily artifact-prone**. Strong green/red
  false-colour regions occur across the face, so this is not a clean pulse result.

### `subway_motion_legacy_0.4-3Hz_a20.avi`

- Source: `data/benchmarks/mit_evm/subway.mp4`
- Implementation: unmodified `data/pyevm/EVM.py` motion path at upstream commit `00649cc`
- Temporal filter: fifth-order causal Butterworth bandpass (`scipy.signal.lfilter`)
- Passband: 0.4--3.0 Hz
- Amplification: 20
- Pyramid levels: 3
- Output: 640x352, 30 FPS, 243 frames
- Assessment: **failed visual-quality baseline**. Severe amplified noise,
  ringing, and clipping dominate the frame.

### `wrist_motion_legacy_halfres_0.4-3Hz_a20.avi`

- Official source: `data/benchmarks/mit_evm/wrist.mp4`
- Processed derivative: `data/derived/wrist_half_resolution.mp4`
- Reason for derivative: the unmodified full-resolution run did not complete
  after approximately seven minutes because the legacy implementation stores
  several full-video float64 tensors in memory
- Derivative: 320x176, 30 FPS, all 894 frames and the full 29.8-second duration
- Implementation: unmodified `data/pyevm/EVM.py` motion path at upstream commit `00649cc`
- Passband: 0.4--3.0 Hz
- Amplification: 20
- Pyramid levels: 3
- Output: 320x176, 30 FPS, 894 frames
- Assessment: **failed visual-quality baseline**. The output remains recognizable
  but contains heavy block noise, ringing, and color artifacts.
