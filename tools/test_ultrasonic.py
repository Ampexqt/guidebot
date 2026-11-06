"""Timing and cleanup checks without GPIO hardware or libgpiod."""
import unittest
from types import SimpleNamespace

from ultrasonic_test import ECHO, TRIG, distance_cm, wait_pulse, clear_events, measure

RISE, FALL = 'rising', 'falling'


def event(kind, timestamp, line=ECHO):
    return SimpleNamespace(event_type=kind, timestamp_ns=timestamp, line_offset=line)


class FakeRequest:
    def __init__(self, batches=(), high=False):
        self.batches = list(batches)
        self.high = high
        self.outputs = []
        self.waits = []

    def wait_edge_events(self, timeout):
        self.waits.append(timeout)
        return bool(self.batches)

    def read_edge_events(self):
        return self.batches.pop(0)

    def get_value(self, line):
        return self.high

    def set_value(self, line, value):
        self.outputs.append((line, value))


class UltrasonicTests(unittest.TestCase):
    def test_kernel_pulse_duration_gives_distance(self):
        request = FakeRequest([[event(RISE, 1000), event(FALL, 1001000)]])
        width = wait_pulse(request, 1000, RISE, FALL)
        self.assertEqual(width, 1000000)
        self.assertAlmostEqual(distance_cm(width), 17.15)

    def test_edges_in_separate_batches_and_stale_edges_ignored(self):
        request = FakeRequest([[event(RISE, 100), event(FALL, 200)],
                               [event(FALL, 1100), event(RISE, 1500)],
                               [event(FALL, 2001500)]])
        self.assertEqual(wait_pulse(request, 1000, RISE, FALL), 2000000)

    def test_unrelated_gpio_edge_does_not_form_measurement(self):
        request = FakeRequest([[event(RISE, 1000, 6), event(FALL, 1001000)]])
        with self.assertRaisesRegex(TimeoutError, 'rising'):
            wait_pulse(request, 1000, RISE, FALL)

    def test_absent_echo_times_out_with_bounded_wait(self):
        request = FakeRequest()
        with self.assertRaisesRegex(TimeoutError, 'rising'):
            wait_pulse(request, 0, RISE, FALL)
        self.assertTrue(all(0 < t <= 0.04 for t in request.waits))

    def test_missing_falling_edge_times_out(self):
        request = FakeRequest([[event(RISE, 1000)]])
        with self.assertRaisesRegex(TimeoutError, 'falling'):
            wait_pulse(request, 1000, RISE, FALL)

    def test_noise_does_not_extend_deadline(self):
        request = FakeRequest([[event(RISE, 0)]] * 100)
        ticks = iter(i * 0.01 for i in range(100))
        with self.assertRaises(TimeoutError):
            wait_pulse(request, 1000, RISE, FALL, clock=lambda: next(ticks))
        self.assertLess(len(request.waits), 5)

    def test_event_drain_is_bounded_when_noisy(self):
        request = FakeRequest([[event(RISE, 0)]] * 100)
        with self.assertRaisesRegex(ValueError, 'continuous'):
            clear_events(request)
        self.assertEqual(len(request.batches), 96)

    def test_stuck_high_echo_does_not_trigger_sensor(self):
        request = FakeRequest(high=True)
        with self.assertRaisesRegex(ValueError, 'already HIGH'):
            measure(request, False, True, RISE, FALL)
        self.assertEqual(request.outputs, [])

    def test_interrupt_during_trigger_restores_low(self):
        request = FakeRequest()

        def interrupt(_):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            measure(request, False, True, RISE, FALL, sleep=interrupt)
        self.assertEqual(request.outputs, [(TRIG, True), (TRIG, False)])

    def test_out_of_range_pulses_are_not_reported_as_distances(self):
        for width in (0, -1, 100, 100000000):
            with self.subTest(width=width), self.assertRaises(ValueError):
                distance_cm(width)


if __name__ == '__main__':
    unittest.main()
