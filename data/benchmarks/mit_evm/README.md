# MIT CSAIL EVM Benchmark Inputs

These source videos were downloaded from the official MIT CSAIL Eulerian Video
Magnification project page for non-commercial course-project evaluation:

<https://people.csail.mit.edu/mrub/evm/>

The MIT page asks users of the supplied videos to cite:

H.-Y. Wu, M. Rubinstein, E. Shih, J. Guttag, F. Durand, and W. T. Freeman,
"Eulerian Video Magnification for Revealing Subtle Changes in the World," ACM
Transactions on Graphics (Proc. SIGGRAPH), 31(4), 2012.

## Files

| File | Intended stress case | Resolution | FPS | Frames | SHA-256 |
|---|---|---:|---:|---:|---|
| `face.mp4` | Subtle facial pulse/color variation | 528x592 | 30 | 301 | `FAB07662AE910808B53F8E2A9150EC88BEB06FECA4A38C2D8D37B92D84FF4AA5` |
| `wrist.mp4` | Localized subtle wrist motion with ROI relevance | 640x352 | 30 | 894 | `9D998B6EA6739C3AB37B0D16343F3491ACE658E9032F15B82E607F303B84A10D` |
| `subway.mp4` | Broader scene motion and artifact sensitivity | 640x352 | 29.97 | 243 | `B43A0369016EC90C321D770AE4CED3F2B54E35DE806AD33129CA565B9E0EFF34` |

Every listed frame was decoded successfully with the project OpenCV environment
after download. Preserve these files unchanged as benchmark inputs; write all
generated videos under `results/`.
