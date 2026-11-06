# EE604 Eulerian Video Magnification

This CPU implementation combines signed Laplacian detail bands, zero-phase
Butterworth filtering, automatic ROI frequency selection, and optional
bilateral smoothing. The final spatial mask prevents the magnification from
changing pixels outside the selected ROI before video encoding.

## Repository layout

- `src/` contains the dashboard, magnification pipeline, and evaluation scripts.
- `data/` contains the benchmark inputs and the attributed PyEVM reference.
- `docs/` contains the report source and evaluation artifacts.
- `tests/` contains the regression tests.

Run the commands below from the repository root.

## Run the demo

Use Python 3.9 or newer and install FFmpeg with the `libx264` encoder on
`PATH` for Streamlit video previews and exports.

```sh
python -m pip install -r requirements.txt
python -m streamlit run src/app2.py
```

Upload `data/derived/wrist_half_resolution.mp4`, select **Automatic ROI** and
**Automatic** frequency, and start at a magnification factor of 4. The
spectrum shows the full PSD and shades the range eligible for peak selection.
The yellow ROI supplies frequency samples. When shown, the larger cyan ROI
is the area the app magnifies. Enable **Artifact suppression** to apply the
bilateral filter to the filtered pyramid details.

## Reproduce the evaluation

```sh
python -m unittest discover -s tests -v
python -m src.benchmark_evm
```

The benchmark applies six matched configurations to the same synthetic,
wrist, baby, and guitar frames. It writes CSV metrics, effective processing
FPS, CVPR table rows, a wrist spectrum, and aligned horizontal space-time
plots to `docs/results/validation/`. Reported processing time excludes decoding
and encoding. It includes PSD estimation for automatic configurations.
Synthetic reference error measures agreement with a known magnified motion.
The real-video metrics describe signal change and spatial leakage.

To evaluate a throat or phone recording, pass its file and ROI in original
video pixels. An optional start and duration select a steady excerpt.

```sh
python -m src.benchmark_evm --video "local clip.mp4" --roi 100 180 60 45 --start 5 --seconds 12 --output temp/custom-validation
```

## Build the report

Open the CVPR 2022 author kit in Overleaf. Keep its `cvpr.sty`, use
`docs/write-up.tex` as the main document, and upload the referenced files under
`docs/results/validation/` and the Python sources at their repository paths.
The appendix reads those source files directly.
