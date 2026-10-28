"""Math-only checks; no GPIO access or external packages required."""
import unittest
import json
import math
from pathlib import Path

from tft_touch_calibrate import TARGETS, fit, project, distance


class CalibrationTests(unittest.TestCase):
    def test_reversed_x_and_scaled_y(self):
        raw = [(3700 - x * 13, 450 + y * 10) for x, y in TARGETS]
        coefficients = fit(raw, TARGETS)
        self.assertLess(distance(project(coefficients, (2140, 2050)), (120, 160)), 1e-7)

    def test_rotated_and_skewed_sensor(self):
        raw = [(500 + 9*y + 0.4*x, 3600 - 12*x + 0.3*y) for x, y in TARGETS]
        coefficients = fit(raw, TARGETS)
        for x, y in [(35, 65), (100, 240), (190, 100)]:
            point = (500 + 9*y + 0.4*x, 3600 - 12*x + 0.3*y)
            self.assertLess(distance(project(coefficients, point), (x, y)), 1e-7)

    def test_small_adc_noise_still_maps_independent_point(self):
        noise = [(9, -8), (-5, 10), (7, -12), (-9, 4), (2, 3)]
        raw = [(3700 - x*13 + nx, 450 + y*10 + ny)
               for (x, y), (nx, ny) in zip(TARGETS, noise)]
        coefficients = fit(raw, TARGETS)
        self.assertLess(distance(project(coefficients, (1750, 1650)), (150, 120)), 2)

    def test_identical_readings_cannot_calibrate(self):
        with self.assertRaises(ValueError):
            fit([(2000, 2000)] * 5, TARGETS)

    def test_collinear_readings_cannot_calibrate(self):
        with self.assertRaises(ValueError):
            fit([(x, 2*x) for x in (400, 1000, 1600, 2200, 2800)], TARGETS)

    def test_saved_bench_calibration_matches_recorded_results(self):
        data = json.loads(Path(__file__).with_name('tft_touch_calibration.json').read_text())
        self.assertEqual((data['width'], data['height']), (240, 320))
        self.assertEqual(data['madctl'], 0x48)
        self.assertEqual(data['raw_divisor'], 4095)
        self.assertEqual(data['targets'], [list(p) for p in TARGETS])
        self.assertEqual(len(data['samples']), 5)
        self.assertEqual(len(data['verification']), 3)
        self.assertEqual(len(data['coefficients']), 2)
        for row in data['coefficients']:
            self.assertEqual(len(row), 3)
            self.assertTrue(all(math.isfinite(v) for v in row))
        errors = [distance(project(data['coefficients'], raw), target)
                  for raw, target in zip(data['samples'], data['targets'])]
        rms = math.sqrt(sum(e * e for e in errors) / len(errors))
        self.assertAlmostEqual(rms, data['fit_rms_pixels'])
        self.assertLessEqual(rms, 12)
        self.assertLessEqual(max(errors), 20)
        for check in data['verification']:
            error = distance(project(data['coefficients'], check['raw']), check['target'])
            self.assertAlmostEqual(error, check['error_pixels'])
            self.assertLessEqual(error, 20)


if __name__ == '__main__':
    unittest.main()
