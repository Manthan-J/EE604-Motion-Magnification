# Derived Benchmark Inputs

This directory contains documented transformations of immutable benchmark inputs.

## `wrist_half_resolution.mp4`

- Source: `data/benchmarks/mit_evm/wrist.mp4`
- Transformation: OpenCV `INTER_AREA` resize from 640x352 to 320x176
- Temporal content: unchanged 30 FPS, 894 frames, 29.8 seconds
- Reason: the unmodified legacy PyEVM implementation could not practically
  process the full-resolution clip because it materializes multiple float64
  tensors for the entire video. Half resolution reduces spatial samples and
  approximate tensor memory by 75% while preserving the full time series.

Do not treat this derivative as identical to the official-resolution benchmark
when reporting spatial-quality metrics.
