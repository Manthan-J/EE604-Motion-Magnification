"""Synthetic regression tests for ROI frequency estimation."""

import unittest

import numpy as np

from auto_frequency import estimate_dominant_frequency, extract_roi_signal


class FrequencyEstimateTests(unittest.TestCase):
    fps = 30.0

    def setUp(self):
        self.time = np.arange(600) / self.fps
        self.tone = np.sin(2 * np.pi * 1.2 * self.time)

    def estimate(self, signal, **kwargs):
        return estimate_dominant_frequency(signal, self.fps, 0.7, 2.5, **kwargs)

    def assert_detected_tone(self, result):
        self.assertTrue(result.reliable, result.message)
        bin_width = result.frequencies[1] - result.frequencies[0]
        self.assertLessEqual(abs(result.peak_hz - 1.2), bin_width / 2)
        self.assertLessEqual(abs(result.bpm - 72.0), 60.0 * bin_width / 2)
        self.assertGreaterEqual(result.confidence, 3.0)
        self.assertEqual(result.frequencies.shape, result.psd.shape)
        self.assertTrue(np.all(np.isfinite(result.psd)))
        self.assertAlmostEqual(result.low_hz, result.peak_hz - 0.2)
        self.assertAlmostEqual(result.high_hz, result.peak_hz + 0.2)

    def assert_no_automatic_band(self, result):
        self.assertFalse(result.reliable)
        self.assertIsNone(result.peak_hz)
        self.assertIsNone(result.bpm)
        self.assertIsNone(result.low_hz)
        self.assertIsNone(result.high_hz)
        self.assertTrue(result.message)

    def test_clean_tone(self):
        self.assert_detected_tone(self.estimate(self.tone))

    def test_noisy_tone(self):
        noise = np.random.default_rng(42).normal(0, 0.8, self.tone.size)
        self.assert_detected_tone(self.estimate(self.tone + noise))

    def test_stronger_out_of_band_tone_and_drift(self):
        outside = 3.0 * np.sin(2 * np.pi * 4.0 * self.time)
        self.assert_detected_tone(self.estimate(self.tone + outside + 0.8 * self.time))

    def test_constant_and_linear_signals(self):
        for signal in (np.full_like(self.time, 120.0), 100.0 + 2.0 * self.time):
            with self.subTest(signal=signal[:3]):
                result = self.estimate(signal)
                self.assert_no_automatic_band(result)
                self.assertGreater(result.psd.size, 0)
                self.assertIn("no variation", result.message)

    def test_short_signal(self):
        result = self.estimate(self.tone[:60])
        self.assert_no_automatic_band(result)
        self.assertIn("too short", result.message)
        self.assertGreater(result.psd.size, 0)

    def test_nonfinite_signal(self):
        for sample in (np.nan, np.inf, -np.inf):
            with self.subTest(sample=sample):
                signal = self.tone.copy()
                signal[100] = sample
                result = self.estimate(signal)
                self.assert_no_automatic_band(result)
                self.assertEqual(result.frequencies.size, 0)

    def test_confidence_threshold(self):
        noise = np.random.default_rng(17).normal(size=self.tone.size)
        result = self.estimate(noise, min_confidence=10.0)
        self.assert_no_automatic_band(result)
        self.assertIn("below the threshold", result.message)
        self.assertGreater(result.confidence, 0)
        self.assertLess(result.confidence, 10.0)
        self.assertGreater(result.psd.size, 0)

    def test_invalid_fps(self):
        for fps in (0.0, -30.0, np.nan, np.inf):
            with self.subTest(fps=fps), self.assertRaisesRegex(ValueError, "FPS"):
                estimate_dominant_frequency(self.tone, fps, 0.7, 2.5)

    def test_invalid_limits(self):
        for min_hz, max_hz in ((0, 2.5), (2.5, 0.7), (0.7, 15), (0.7, 20)):
            with self.subTest(limits=(min_hz, max_hz)), self.assertRaisesRegex(ValueError, "Nyquist"):
                estimate_dominant_frequency(self.tone, self.fps, min_hz, max_hz)

    def test_empty_and_malformed_signals(self):
        for signal in ([], [[1, 2, 3]]):
            with self.subTest(signal=signal), self.assertRaisesRegex(ValueError, "one-dimensional"):
                self.estimate(signal)

    def test_peak_at_upper_search_boundary(self):
        result = estimate_dominant_frequency(self.tone, self.fps, 0.6, 1.2)
        self.assertTrue(result.reliable, result.message)
        self.assertAlmostEqual(result.peak_hz, 1.2)
        self.assertEqual(result.high_hz, 1.2)

    def test_nyquist_safety_margin(self):
        tone = np.sin(2 * np.pi * 14.1 * self.time)
        result = estimate_dominant_frequency(tone, self.fps, 13.5, 14.9)
        self.assertTrue(result.reliable, result.message)
        self.assertAlmostEqual(result.high_hz, 0.95 * self.fps / 2)

        tone = np.sin(2 * np.pi * 14.3 * self.time)
        result = estimate_dominant_frequency(tone, self.fps, 13.5, 14.9)
        self.assert_no_automatic_band(result)
        self.assertIn("Nyquist safety margin", result.message)


class RoiExtractionTests(unittest.TestCase):
    def setUp(self):
        self.frames = np.full((2, 3, 4, 3), 255, dtype=np.uint8)
        self.frames[0, 1, 2:4] = [(10, 20, 30), (30, 40, 50)]
        self.frames[1, 1, 2:4] = [(50, 100, 170), (70, 120, 190)]

    def test_green_gray_and_mean(self):
        roi = (2, 1, 2, 1)
        np.testing.assert_allclose(extract_roi_signal(self.frames, roi), [30, 110])
        np.testing.assert_allclose(
            extract_roi_signal(self.frames, roi, "gray"), [31.85, 125.23]
        )
        np.testing.assert_allclose(
            extract_roi_signal(self.frames, roi, "mean"), [30, 350 / 3]
        )

    def test_invalid_and_out_of_frame_roi(self):
        for roi in ((-1, 0, 2, 1), (3, 0, 2, 1), (0, 2, 1, 2),
                    (0, 0, 0, 1), (0, 0, 1, -1), (0, 0, 1.5, 1), (0, 0, 1)):
            with self.subTest(roi=roi), self.assertRaisesRegex(ValueError, "ROI"):
                extract_roi_signal(self.frames, roi)

    def test_unsupported_channel(self):
        with self.assertRaisesRegex(ValueError, "Channel"):
            extract_roi_signal(self.frames, (0, 0, 2, 2), "red")
