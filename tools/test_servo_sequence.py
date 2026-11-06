"""Simulated I2C checks; never opens a physical bus."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from servo_sequence_test import PCA9685, PULSES_US, run_sequence, main


class FakeBus:
    def __init__(self, fail_at=None, external_clock=False):
        self.active = set()
        self.pulses = []
        self.failure = fail_at
        self.external_clock = external_clock
        self.off_attempts = []
        self.closed = False

    def close(self):
        self.closed = True

    def read_byte_data(self, address, register):
        return 0x40 if self.external_clock else 0

    def write_byte_data(self, address, register, value):
        if register in range(0x09, 0x46, 4) and value == 0x10:
            channel = (register - 0x09) // 4
            self.off_attempts.append(channel)
            self.active.discard(channel)

    def write_i2c_block_data(self, address, register, values):
        channel = (register - 0x06) // 4
        if self.failure == len(self.pulses):
            self.failure = None
            raise OSError('simulated bus interruption')
        self.active.add(channel)
        if len(self.active) > 1:
            raise AssertionError('Multiple servos received pulses simultaneously')
        self.pulses.append((channel, values))


class ServoSequenceTests(unittest.TestCase):
    def make_controller(self, bus):
        return PCA9685(bus, sleep=lambda _: None)

    def test_enter_gates_each_channel_and_pause_separates_them(self):
        bus = FakeBus()
        delays = []
        prompts = []

        def enter(prompt):
            self.assertFalse(bus.active)
            self.assertEqual(len(bus.pulses), len(prompts) * len(PULSES_US))
            prompts.append(prompt)
            return ''

        completed = run_sequence(self.make_controller(bus), read=enter,
                                 write=lambda _: None, sleep=delays.append, pause=3)
        self.assertEqual(completed, [0, 1, 2, 3])
        self.assertEqual([ch for ch, _ in bus.pulses], [ch for ch in range(4) for _ in PULSES_US])
        self.assertEqual(delays, ([1.0] * 5 + [3]) * 3 + [1.0] * 5)
        self.assertEqual(len(prompts), 4)
        self.assertFalse(bus.active)

    def test_quit_without_enter_never_sends_movement(self):
        bus = FakeBus()
        result = run_sequence(self.make_controller(bus), read=lambda _: 'q', write=lambda _: None)
        self.assertEqual(result, [])
        self.assertEqual(bus.pulses, [])
        self.assertEqual(set(bus.off_attempts), set(range(16)))

    def test_quit_after_first_channel_leaves_others_untested(self):
        bus = FakeBus()
        replies = iter(['', 'q'])
        result = run_sequence(self.make_controller(bus), read=lambda _: next(replies),
                              write=lambda _: None, sleep=lambda _: None)
        self.assertEqual(result, [0])
        self.assertEqual({ch for ch, _ in bus.pulses}, {0})
        self.assertFalse(bus.active)

    def test_ctrl_c_during_motion_disables_outputs(self):
        bus = FakeBus()

        def interrupt(_):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            run_sequence(self.make_controller(bus), read=lambda _: '',
                         write=lambda _: None, sleep=interrupt)
        self.assertFalse(bus.active)
        self.assertEqual(set(bus.off_attempts[-16:]), set(range(16)))

    def test_bus_error_prevents_later_servos_and_attempts_cleanup(self):
        bus = FakeBus(fail_at=2)
        with self.assertRaises(OSError):
            run_sequence(self.make_controller(bus), read=lambda _: '',
                         write=lambda _: None, sleep=lambda _: None)
        self.assertEqual({ch for ch, _ in bus.pulses}, {0})
        self.assertFalse(bus.active)
        self.assertEqual(set(bus.off_attempts[-16:]), set(range(16)))

    def test_closed_input_disables_outputs(self):
        bus = FakeBus()

        def eof(_):
            raise EOFError

        with self.assertRaises(EOFError):
            run_sequence(self.make_controller(bus), read=eof, write=lambda _: None)
        self.assertFalse(bus.active)

    def test_external_clock_is_rejected_before_movement(self):
        bus = FakeBus(external_clock=True)
        with self.assertRaises(RuntimeError):
            run_sequence(self.make_controller(bus), read=lambda _: '', write=lambda _: None)
        self.assertFalse(bus.pulses)

    def test_cleanup_tries_remaining_channels_after_write_error(self):
        bus = FakeBus()
        original = bus.write_byte_data

        def fail_one(address, register, value):
            if register == 0x09:
                raise OSError('channel zero off failed')
            original(address, register, value)

        bus.write_byte_data = fail_one
        with self.assertRaises(OSError):
            self.make_controller(bus).off_all()
        self.assertEqual(bus.off_attempts, list(range(1, 16)))

    def run_main_with_bus(self, bus, reply):
        def sequence(controller, pause):
            return run_sequence(controller, read=lambda _: reply, write=lambda _: None,
                                sleep=lambda _: None, pause=pause)

        # FakeBus deliberately has no context manager methods, matching the
        # python3-smbus interface reported by the user's board.
        module = SimpleNamespace(SMBus=lambda index: bus)
        with patch.dict('sys.modules', {'smbus': module}), \
             patch('sys.argv', ['servo_sequence_test.py']), \
             patch('servo_sequence_test.run_sequence', side_effect=sequence), \
             patch('builtins.print'):
            return main()

    def test_main_supports_bus_without_context_manager_and_closes_on_quit(self):
        bus = FakeBus()
        self.assertEqual(self.run_main_with_bus(bus, 'q'), 0)
        self.assertTrue(bus.closed)
        self.assertFalse(bus.active)
        self.assertFalse(bus.pulses)

    def test_main_closes_non_context_manager_bus_after_i2c_error(self):
        bus = FakeBus(fail_at=0)
        self.assertEqual(self.run_main_with_bus(bus, ''), 1)
        self.assertTrue(bus.closed)
        self.assertFalse(bus.active)
        self.assertEqual(set(bus.off_attempts[-16:]), set(range(16)))


if __name__ == '__main__':
    unittest.main()
