"""Integrated navigation and failures exercised without GPIO or a sound card."""

import json
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import Mock, patch

from guidebot.database import CampusDatabase, DEFAULT_DATABASE
from guidebot.robot import RobotSession, load_calibration, CALIBRATION, main, hit
from guidebot.robot_devices import BenchMotion, Speech, RangeSensor


class RobotTests(unittest.TestCase):
    def setUp(self):
        self.speech = Mock()
        self.speech.active = False
        self.motion = Mock()
        self.session = RobotSession(CampusDatabase(DEFAULT_DATABASE), self.speech, self.motion)

    def test_arrival_hysteresis_cooldown_and_dropouts(self):
        for now, cm in ((0, 30), (1, None), (2, 30), (3, 47)):
            self.session.tick(now, cm)
        self.assertEqual(self.speech.say.call_count, 1)
        self.session.tick(4, 60)
        self.session.tick(5, 30)
        self.assertEqual(self.speech.say.call_count, 1)
        self.session.tick(20, 60)
        self.session.tick(21, 30)
        self.assertEqual(self.speech.say.call_count, 2)
        self.motion.start.assert_called_with(0)

    def test_menu_interrupts_speech_and_destination_is_spoken(self):
        self.session.say('Welcome')
        self.session.action('menu')
        self.speech.close.assert_called_once()
        self.assertFalse(self.session.talking)
        self.session.action('destination:library')
        self.assertEqual(self.session.page, 'face')
        text = self.speech.say.call_args.args[0]
        self.assertIn('fictional campus directions', text)
        self.assertIn('Library', text)
        self.motion.start.assert_called_once_with(1)

    def test_repeat_disabled_during_playback_then_replays_same_text(self):
        self.session.action('repeat')
        self.speech.say.assert_not_called()
        self.session.say('Remember this')
        self.session.action('repeat')
        self.assertEqual(self.speech.say.call_count, 1)
        self.session.tick(0, None)
        self.session.action('repeat')
        self.assertEqual(self.speech.say.call_count, 2)
        self.speech.say.assert_called_with('Remember this')

    def test_no_greeting_over_menu_or_active_audio(self):
        self.session.action('menu')
        self.session.tick(0, 30)
        self.speech.say.assert_not_called()
        self.session.action('home')
        self.session.tick(20, 60)
        self.speech.active = True
        self.session.tick(21, 30)
        self.speech.say.assert_not_called()

    def test_motion_is_optional_and_channel_tests_are_explicit(self):
        self.session.motion = None
        self.session.action('motor:0')
        self.session.action('destination:registrar')
        self.motion.start.assert_not_called()
        self.session.motion = self.motion
        self.session.action('motor:3')
        self.motion.start.assert_called_once_with(3)

    def test_calibration_real_file_and_reject_invalid_orientation_or_nan(self):
        self.assertEqual(len(load_calibration(CALIBRATION)), 2)
        data = json.loads(CALIBRATION.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'calibration.json'
            for key, value in [('width', 320), ('coefficients', [[float('nan'), 1, 1], [1, 1, 1]])]:
                bad = dict(data, **{key: value})
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_calibration(path)

    def test_check_never_opens_hardware(self):
        with patch('guidebot.robot_devices.ServoDevice') as servo:
            self.assertEqual(main(['--check']), 0)
            servo.assert_not_called()

    def test_hit_targets_ignore_gaps(self):
        buttons = [((10, 20, 80, 90), 'repeat')]
        self.assertEqual(hit(buttons, (40, 50)), 'repeat')
        self.assertIsNone(hit(buttons, (100, 100)))

    def test_runtime_failure_closes_all_opened_devices(self):
        with patch('guidebot.robot_devices.Speech') as speech, \
                patch('guidebot.robot_devices.ServoDevice') as servo, \
                patch('guidebot.robot_devices.RangeSensor') as sensor, \
                patch('tools.tft_touch_calibrate.Hardware') as hardware, \
                patch.dict(sys.modules, {'PIL': Mock()}):
            sensor.return_value.snapshot.side_effect = OSError('sensor failure')
            self.assertEqual(main(['--bench-motion']), 1)
            speech.return_value.close.assert_called_once()
            servo.return_value.close.assert_called_once()
            sensor.return_value.close.assert_called_once()
            hardware.return_value.__exit__.assert_called_once()

    def test_display_open_failure_still_disables_servo_outputs(self):
        with patch('guidebot.robot_devices.Speech') as speech, \
                patch('guidebot.robot_devices.ServoDevice') as servo, \
                patch('guidebot.robot_devices.RangeSensor') as sensor, \
                patch('tools.tft_touch_calibrate.Hardware') as hardware, \
                patch.dict(sys.modules, {'PIL': Mock()}):
            hardware.return_value.__enter__.side_effect = OSError('SPI missing')
            self.assertEqual(main(['--bench-motion']), 1)
            speech.return_value.close.assert_called_once()
            servo.return_value.close.assert_called_once()
            sensor.assert_not_called()


class DeviceTests(unittest.TestCase):
    def test_motion_is_timed_serial_and_disables_output(self):
        controller = Mock()
        now = [0]
        motion = BenchMotion(controller, lambda: now[0])
        motion.start(2)
        motion.start(3)  # Cannot overlap.
        for value in range(6):
            now[0] = value
            motion.update()
            motion.update()  # No extra step before deadline.
        self.assertEqual([c.args for c in controller.pulse.call_args_list],
                         [(2, n) for n in (1500, 1400, 1500, 1600, 1500)])
        controller.off.assert_called_once_with(2)
        self.assertFalse(motion.active)
        motion.close()
        controller.off_all.assert_called_once()

    def test_failed_player_launch_terminates_synthesizer(self):
        source = Mock()
        source.poll.return_value = None
        with patch('guidebot.robot_devices.subprocess.Popen', side_effect=[source, OSError('missing aplay')]):
            speech = Speech('USB')
            with self.assertRaises(OSError):
                speech.say('Hello')
        source.terminate.assert_called_once()
        source.wait.assert_called_once()
        source.stdout.close.assert_called_once()
        self.assertFalse(speech.active)

    def test_playback_failure_is_reported_and_processes_reaped(self):
        speech = Speech('USB')
        speech.children = [Mock(), Mock()]
        speech.children[0].poll.return_value = 0
        speech.children[1].poll.return_value = 1
        with self.assertRaises(RuntimeError):
            _ = speech.active
        self.assertEqual(speech.children, [])

    def test_stale_sensor_cannot_trigger_greeting(self):
        import threading
        sensor = RangeSensor.__new__(RangeSensor)
        sensor.lock = threading.Lock()
        sensor.sample = (20, None, 10)
        with patch('guidebot.robot_devices.time.monotonic', return_value=13):
            self.assertEqual(sensor.snapshot(), (None, 'Sensor reading stale'))


if __name__ == '__main__':
    unittest.main()
