import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from guidebot.controller import Page, RobotController
from guidebot.database import CampusDatabase, DEFAULT_DATABASE
from guidebot.hardware.simulated import SimulatedServos, SimulatedUltrasonic
from guidebot.headless import TerminalSession, run_headless, snapshot


class HeadlessTests(unittest.TestCase):
    def setUp(self):
        self.db = CampusDatabase(DEFAULT_DATABASE)
        self.sensor = SimulatedUltrasonic()
        self.c = RobotController(self.db, SimulatedServos(), self.sensor)
        self.output = io.StringIO()
        self.session = TerminalSession(self.c, self.sensor, self.output)
        self.addCleanup(self.c.close)

    def test_once_outputs_only_one_json_snapshot(self):
        result = run_headless(self.db, once=True, output=self.output)
        lines = self.output.getvalue().splitlines()
        self.assertEqual(result, 0)
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["mode"], "simulation")
        self.assertTrue(data["placeholder"])
        self.assertEqual(len(data["servo_angles"]), 4)
        self.assertEqual(data["distance_cm"], 80)

    def test_bounded_monitor_advances_and_sleeps_between_snapshots(self):
        with patch("guidebot.headless.time.sleep") as sleep:
            with patch("guidebot.headless.time.monotonic", side_effect=[0, .2, .4]):
                result = run_headless(self.db, steps=3, interval=.2, output=self.output)
        self.assertEqual(result, 0)
        data = [json.loads(line) for line in self.output.getvalue().splitlines()]
        self.assertEqual([item["simulated_seconds"] for item in data], [0, .2, .4])
        self.assertEqual(sleep.call_count, 2)
        self.assertNotEqual(data[0]["distance_cm"], data[-1]["distance_cm"])

    def test_monitor_stops_cleanly_on_ctrl_c(self):
        with patch("guidebot.headless.time.sleep", side_effect=KeyboardInterrupt):
            self.assertEqual(run_headless(self.db, monitor=True, output=self.output), 0)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)

    def test_terminal_search_route_steps_and_navigation(self):
        self.session.execute("search books")
        self.assertIn("library: Library", self.output.getvalue())
        self.session.execute("go library")
        self.assertEqual(snapshot(self.c)["step_number"], 1)
        self.session.execute("next")
        self.assertEqual(snapshot(self.c)["step_number"], 2)
        self.session.execute("previous")
        self.session.execute("back")
        self.assertEqual(self.c.page, Page.MENU)
        self.assertEqual(self.c.query, "books")
        self.session.execute("home")
        self.assertEqual(self.c.page, Page.WELCOME)
        self.assertFalse(self.session.execute("quit"))

    def test_every_gesture_works_in_terminal(self):
        self.sensor.automatic = False
        for name in ("wave", "nod", "look", "point", "neutral"):
            with self.subTest(name=name):
                self.session.execute(f"gesture {name}")
                self.assertEqual(self.c.servos.active_gesture, name)
                self.session.execute("tick 2")
                self.assertEqual(self.c.servos.active_gesture, "idle")

    def test_manual_distance_and_automatic_restore(self):
        self.session.execute("distance 30")
        self.assertFalse(self.sensor.automatic)
        self.assertEqual(self.c.distance_cm, 30)
        self.assertTrue(self.c.nearby)
        self.session.execute("distance auto")
        self.assertTrue(self.sensor.automatic)

    def test_invalid_command_arguments_are_rejected(self):
        for command in ("dance", "next extra", "list extra", "go missing", "tick nan",
                        "tick -1", "tick 61", "distance 401", "gesture fly", 'go "unterminated'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.session.execute(command)
        self.assertIsNone(self.c.motion_error)

    def test_interactive_error_recovers_and_eof_exits(self):
        stream = io.StringIO("go missing\nsearch records\ngo registrar\nnext\nstatus\n")
        with self.assertLogs("guidebot.headless", level="WARNING"):
            self.assertEqual(run_headless(self.db, input_stream=stream, output=self.output), 0)
        text = self.output.getvalue()
        self.assertIn("Error:", text)
        self.assertIn("registrar: Registrar", text)
        snapshots = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
        self.assertEqual(snapshots[-1]["destination"], "Registrar")
        self.assertEqual(snapshots[-1]["step_number"], 2)
        self.assertIn("placeholder", snapshots[-1]["instruction"])

    def test_cleanup_runs_on_output_failure(self):
        class BrokenOutput(io.StringIO):
            def write(self, _text):
                raise BrokenPipeError()
        with patch("guidebot.headless.RobotController", return_value=self.c):
            self.assertEqual(run_headless(self.db, once=True, output=BrokenOutput()), 0)
        self.assertTrue(self.c.closed)

    def test_headless_process_cannot_import_gui_or_real_drivers(self):
        # Proves headless operation works when Tk and hardware libraries are absent.
        with tempfile.TemporaryDirectory() as folder:
            script = """
import importlib.abc
import sys
class BlockedImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter', 'RPi', 'smbus', 'smbus2', 'spidev', 'gpiod') or fullname == 'guidebot.hardware.future':
            raise RuntimeError('Forbidden import: ' + fullname)
sys.meta_path.insert(0, BlockedImports())
from guidebot.__main__ import main
raise SystemExit(main(sys.argv[1:]))
"""
            result = subprocess.run([sys.executable, "-c", script, "--headless", "--once",
                                     "--log-file", str(Path(folder)/"test.log")],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                    text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "simulation")
