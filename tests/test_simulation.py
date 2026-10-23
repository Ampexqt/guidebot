import math
import unittest

from guidebot.hardware.future import (HardwareDisabledError, HCSR04DistanceSensor,
                                      PCA9685ServoDriver, SPITFTDisplay)
from guidebot.hardware.simulated import GESTURES, NEUTRAL, SimulatedServos, SimulatedUltrasonic


class ServoTests(unittest.TestCase):
    def test_starts_neutral_and_angle_mapping_is_read_only(self):
        servos = SimulatedServos()
        self.assertEqual(dict(servos.angles), NEUTRAL)
        with self.assertRaises(TypeError):
            servos.angles["head_pan"] = 30

    def test_every_gesture_moves_and_returns_to_neutral(self):
        for name in GESTURES:
            with self.subTest(gesture=name):
                servos = SimulatedServos()
                servos.gesture(name)
                servos.update(0.15)
                if name != "neutral":
                    self.assertNotEqual(dict(servos.angles), NEUTRAL)
                for _ in range(80):
                    servos.update(0.05)
                    self.assertTrue(all(0 <= angle <= 180 for angle in servos.angles.values()))
                self.assertEqual(servos.active_gesture, "idle")
                self.assertEqual(dict(servos.angles), NEUTRAL)

    def test_large_update_finishes_all_keyframes(self):
        servos = SimulatedServos()
        servos.gesture("wave")
        servos.update(10)
        self.assertEqual(dict(servos.angles), NEUTRAL)
        self.assertEqual(servos.active_gesture, "idle")

    def test_reset_interrupts_motion_without_jumping(self):
        servos = SimulatedServos()
        servos.gesture("look")
        servos.update(0.2)
        interrupted = dict(servos.angles)
        servos.gesture("neutral")
        self.assertEqual(dict(servos.angles), interrupted)
        servos.update(1)
        self.assertEqual(dict(servos.angles), NEUTRAL)

    def test_unknown_gesture_and_bad_time(self):
        servos = SimulatedServos()
        with self.assertRaises(ValueError):
            servos.gesture("fly")
        for dt in (-1, math.inf, math.nan):
            with self.subTest(dt=dt), self.assertRaises(ValueError):
                servos.update(dt)

    def test_shutdown_stops_motion_and_rejects_new_gestures(self):
        servos = SimulatedServos()
        servos.gesture("wave")
        servos.close()
        servos.update(2)
        self.assertEqual(servos.active_gesture, "idle")
        with self.assertRaises(RuntimeError):
            servos.gesture("wave")


class SensorTests(unittest.TestCase):
    def test_automatic_readings_change_within_range(self):
        sensor = SimulatedUltrasonic()
        values = []
        for _ in range(250):
            sensor.update(0.1)
            values.append(sensor.read_cm())
        self.assertGreater(max(values)-min(values), 90)
        self.assertTrue(all(2 <= value <= 400 for value in values))

    def test_manual_distance_is_exact(self):
        sensor = SimulatedUltrasonic()
        sensor.automatic = False
        sensor.set_manual_cm(32.5)
        sensor.update(20)
        self.assertEqual(sensor.read_cm(), 32.5)

    def test_invalid_manual_distances_and_time(self):
        sensor = SimulatedUltrasonic()
        for value in (1, 401, math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sensor.set_manual_cm(value)
        for value in (-1, math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sensor.update(value)

    def test_closed_sensor_has_no_reading(self):
        sensor = SimulatedUltrasonic()
        sensor.close()
        with self.assertRaises(RuntimeError):
            sensor.read_cm()

    def test_real_drivers_are_explicitly_disabled(self):
        for driver in (PCA9685ServoDriver, HCSR04DistanceSensor, SPITFTDisplay):
            with self.subTest(driver=driver.__name__), self.assertRaises(HardwareDisabledError):
                driver()
