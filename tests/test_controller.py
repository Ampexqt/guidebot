import math
import unittest
from unittest.mock import patch

from guidebot.controller import Page, RobotController
from guidebot.database import CampusDatabase, DEFAULT_DATABASE, DatabaseError
from guidebot.hardware.simulated import SimulatedServos, SimulatedUltrasonic


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.sensor = SimulatedUltrasonic()
        self.sensor.automatic = False
        self.servos = SimulatedServos()
        self.c = RobotController(CampusDatabase(DEFAULT_DATABASE), self.servos, self.sensor)
        self.addCleanup(self.c.close)

    def test_initial_state_is_welcome_and_friendly(self):
        self.assertEqual(self.c.page, Page.WELCOME)
        self.assertEqual(self.c.expression, "friendly")
        self.assertEqual(self.c.state, "Ready to welcome")

    def test_navigation_search_steps_back_and_home(self):
        self.c.show_menu()
        self.c.search("books")
        self.c.select(self.c.results[0].id)
        self.assertEqual(self.c.page, Page.DIRECTIONS)
        self.c.change_step(1)
        self.assertEqual(self.c.step_index, 1)
        self.c.change_step(99)
        self.assertEqual(self.c.step_index, 2)
        self.c.change_step(-99)
        self.assertEqual(self.c.step_index, 0)
        self.c.back()
        self.assertEqual(self.c.page, Page.MENU)
        self.assertEqual(self.c.query, "books")
        self.c.back()
        self.assertEqual(self.c.page, Page.WELCOME)
        self.assertEqual(self.c.query, "")
        self.assertIsNone(self.c.destination)
        self.c.back()
        self.assertEqual(self.c.page, Page.WELCOME)

    def test_select_invalid_destination_does_not_change_page(self):
        self.c.show_menu()
        with self.assertRaises(DatabaseError):
            self.c.select("missing")
        self.assertEqual(self.c.page, Page.MENU)

    def test_new_destination_starts_at_first_step(self):
        self.c.select("library")
        self.c.change_step(2)
        self.c.select("registrar")
        self.assertEqual(self.c.step_index, 0)

    def test_failed_pointing_gesture_does_not_block_directions(self):
        with patch.object(self.servos, "gesture", side_effect=OSError("simulated offline servo")):
            with self.assertLogs("guidebot.controller", level="ERROR"):
                self.c.select("library")
        self.assertEqual(self.c.page, Page.DIRECTIONS)
        self.assertEqual(self.c.destination.id, "library")
        self.assertIn("offline servo", self.c.motion_error)
        self.c.change_step(1)
        self.assertEqual(self.c.step_index, 1)

    def test_nearby_visitor_triggers_welcome_gesture(self):
        self.sensor.set_manual_cm(30)
        self.c.tick(0.1)
        self.assertTrue(self.c.nearby)
        self.assertEqual(self.servos.active_gesture, "wave")
        self.assertEqual(self.c.expression, "happy")

    def test_nearby_visitor_does_not_interrupt_directions(self):
        self.c.select("library")
        self.sensor.set_manual_cm(30)
        self.c.tick(0.1)
        self.assertEqual(self.servos.active_gesture, "point")
        self.assertEqual(self.c.page, Page.DIRECTIONS)

    def test_proximity_hysteresis_and_greeting_cooldown(self):
        self.sensor.set_manual_cm(44)
        self.c.tick(0.1)
        self.c.tick(2)
        self.assertEqual(self.servos.active_gesture, "idle")
        self.sensor.set_manual_cm(48)
        self.c.tick(0.1)
        self.assertTrue(self.c.nearby)
        self.sensor.set_manual_cm(51)
        self.c.tick(0.1)
        self.assertFalse(self.c.nearby)
        self.sensor.set_manual_cm(40)
        self.c.tick(0.1)
        self.assertEqual(self.servos.active_gesture, "idle")
        self.sensor.set_manual_cm(60)
        self.c.tick(9)
        self.sensor.set_manual_cm(30)
        self.c.tick(0.1)
        self.assertEqual(self.servos.active_gesture, "wave")

    def test_sensor_error_and_recovery(self):
        with patch.object(self.sensor, "read_cm", side_effect=OSError("simulated timeout")):
            with self.assertLogs("guidebot.controller", level="ERROR"):
                self.c.tick(0.1)
            self.assertIsNone(self.c.distance_cm)
            self.assertIn("timeout", self.c.sensor_error)
            self.assertEqual(self.c.expression, "concerned")
            self.c.show_menu()
            self.assertEqual(len(self.c.results), 4)
        self.c.tick(0.1)
        self.assertIsNone(self.c.sensor_error)
        self.assertEqual(self.c.distance_cm, 100)

    def test_impossible_sensor_values_are_errors(self):
        for value in (math.nan, math.inf, -1, 401):
            with self.subTest(value=value), patch.object(self.sensor, "read_cm", return_value=value):
                with self.assertLogs("guidebot.controller", level="ERROR"):
                    self.c.tick(0.1)
                self.assertIsNone(self.c.distance_cm)
            self.c.tick(0.1)

    def test_servo_update_error_keeps_sensor_and_navigation_working(self):
        with patch.object(self.servos, "update", side_effect=OSError("simulated servo error")):
            with self.assertLogs("guidebot.controller", level="ERROR"):
                self.c.tick(0.1)
        self.assertEqual(self.c.distance_cm, 100)
        self.assertIn("servo error", self.c.motion_error)
        self.c.gesture("neutral")
        self.assertIsNone(self.c.motion_error)

    def test_bad_dt_rejected(self):
        for value in (-1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.c.tick(value)

    def test_shutdown_is_idempotent(self):
        self.c.close()
        self.c.close()
        self.c.tick(1)
        self.assertTrue(self.servos.closed)
        self.assertTrue(self.sensor.closed)
