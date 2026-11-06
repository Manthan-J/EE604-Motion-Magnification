"""Regression checks for ROI magnification and video round trips."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from roi_magnification import (
    build_laplacian_pyramid,
    butter_bandpass_filter,
    load_video,
    magnify_frames,
    magnify_motion_with_roi,
    make_roi_mask,
    save_video,
)


class RoiMagnificationTests(unittest.TestCase):
    def test_odd_frame_has_signed_laplacian_bands(self):
        frame = np.zeros((65, 97), dtype=np.uint8)
        frame[16:48, 28:64] = 200
        bands = build_laplacian_pyramid(frame)
        self.assertEqual([b.shape for b in bands], [(17, 25), (33, 49), (65, 97)])
        self.assertLess(bands[-1].min(), 0)

    def test_static_input_has_no_startup_pulse(self):
        data = np.full((90, 2, 3), 100.0)
        filtered = butter_bandpass_filter(data, 0.8, 1.6, 30)
        np.testing.assert_allclose(filtered, 0, atol=1e-9)

    def test_small_roi_keeps_peak_and_no_spillover(self):
        mask = make_roi_mask((11, 13), (4, 3, 3, 3))
        self.assertEqual(mask[4, 5], 1)
        self.assertEqual(np.count_nonzero(mask), 9)

    def test_magnification_preserves_outside_and_channel_differences(self):
        fps = 30
        time = np.arange(150) / fps
        wave = np.rint(15 * np.sin(2 * np.pi * 1.2 * time)).astype(np.int16)
        frames = np.broadcast_to(
            np.array([65, 95, 125], dtype=np.uint8), (len(time), 35, 65, 3)
        ).copy()
        for start in (10, 47):
            frames[:, 10:26, start:start + 8] += (50 + wave).astype(np.uint8)[:, None, None, None]
        box = (6, 5, 25, 25)
        for suppression in (False, True):
            with self.subTest(suppression=suppression):
                output = magnify_frames(
                    frames, fps, 0.8, 1.6, roi=box, artifact_suppression=suppression,
                )
                diff = output.astype(np.int16) - frames
                self.assertTrue(np.any(diff[:, 5:30, 6:31]))
                diff[:, 5:30, 6:31] = 0
                self.assertFalse(np.any(diff))
                np.testing.assert_array_equal(
                    np.diff(output.astype(np.int16), axis=-1),
                    np.diff(frames.astype(np.int16), axis=-1),
                )

    def test_lossless_video_keeps_fractional_fps_and_pads_odd_edges(self):
        frames = np.arange(4 * 17 * 33 * 3, dtype=np.int32).reshape(4, 17, 33, 3)
        frames = frames.astype(np.uint8)
        with TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "test.avi"
            save_video(frames, 29.97, path)
            decoded, fps = load_video(path)
        self.assertAlmostEqual(fps, 29.97, places=2)
        expected = np.pad(frames, ((0, 0), (0, 1), (0, 1), (0, 0)), mode="edge")
        np.testing.assert_array_equal(decoded, expected)

    def test_cancel_does_not_write_video(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.avi"
            frames = np.zeros((2, 16, 16, 3), dtype=np.uint8)
            with patch("roi_magnification.load_video", return_value=(frames, 30)), patch(
                "roi_magnification.select_interactive_roi", return_value=None
            ):
                result = magnify_motion_with_roi("input.avi", 0.8, 1.6, output_path=output)
            self.assertIsNone(result)
            self.assertFalse(output.exists())

    def test_auto_frequency_uses_selected_rectangle_for_detection_and_mask(self):
        fps = 30
        time = np.arange(360) / fps
        frames = np.full((len(time), 16, 32, 3), 100, dtype=np.uint8)
        roi = (5, 3, 10, 8)
        target = np.rint(100 + 8 * np.sin(2 * np.pi * 1.2 * time))
        distractor = np.rint(100 + 30 * np.sin(2 * np.pi * 2.0 * time))
        frames[:, 3:11, 5:15, 1] = target[:, None, None]
        frames[:, :, 16:, 1] = distractor[:, None, None]
        with patch("roi_magnification.load_video", return_value=(frames, fps)), patch(
            "roi_magnification.cv2.selectROI", return_value=roi
        ) as select, patch("roi_magnification.cv2.destroyWindow"), patch(
            "roi_magnification._magnified_frames"
        ) as magnify, patch("roi_magnification.save_video"), patch("builtins.print"):
            magnify_motion_with_roi("input.avi", 0.4, 0.8, auto_search=(0.65, 3.0))
        select.assert_called_once()
        self.assertAlmostEqual(magnify.call_args.args[2], 1.0)
        self.assertAlmostEqual(magnify.call_args.args[3], 1.4)
        np.testing.assert_array_equal(magnify.call_args.args[-1], make_roi_mask((16, 32), roi))

    def test_auto_frequency_uses_manual_band_when_roi_has_no_variation(self):
        frames = np.full((300, 16, 16, 3), 80, dtype=np.uint8)
        with patch("roi_magnification.load_video", return_value=(frames, 30)), patch(
            "roi_magnification._magnified_frames"
        ) as magnify, patch("roi_magnification.save_video"), patch("builtins.print"):
            magnify_motion_with_roi("input.avi", 0.4, 1.0, roi=(2, 3, 8, 8),
                                    auto_search=(0.65, 3.0))
        self.assertEqual(magnify.call_args.args[2:4], (0.4, 1.0))

    def test_invalid_band_is_rejected(self):
        frames = np.zeros((10, 16, 16, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "Passband"):
            magnify_frames(frames, 30, 0.8, 15.0)


if __name__ == "__main__":
    unittest.main()
