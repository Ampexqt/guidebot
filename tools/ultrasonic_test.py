#!/usr/bin/env python3
"""HC-SR04 bench test for Orange Pi One / libgpiod 2.x.

PHYSICAL pins: VCC=2 (5V), GND=14, TRIG=29 (PA7), divided ECHO=31 (PA8).
Use a suitable Echo divider; never connect the 5V Echo directly to GPIO.
Uses kernel edge timestamps and bounded waits. Does not command any motor.
"""

import argparse
import math
import time

TRIG, ECHO = 7, 8  # GPIO offsets, not physical header positions.


def distance_cm(width_ns):
    if width_ns <= 0:
        raise ValueError('Invalid Echo pulse duration.')
    result = width_ns / 1_000_000_000 * 34300 / 2
    if not 2 <= result <= 400:
        raise ValueError(f'Pulse corresponds to {result:.1f} cm, outside the 2-400 cm test range.')
    return result


def wait_pulse(request, after_ns, rising, falling, timeout=0.04, clock=time.monotonic):
    deadline = clock() + timeout
    rise_ns = None
    while True:
        remaining = deadline - clock()
        if remaining <= 0 or not request.wait_edge_events(timeout=remaining):
            phase = 'falling edge' if rise_ns is not None else 'rising edge'
            raise TimeoutError(f'No Echo {phase} within {timeout * 1000:g} ms.')
        for event in request.read_edge_events():
            if event.line_offset != ECHO or event.timestamp_ns < after_ns:
                continue
            if event.event_type == rising:
                rise_ns = event.timestamp_ns
            elif event.event_type == falling and rise_ns is not None:
                width = event.timestamp_ns - rise_ns
                if width <= 0 or width > timeout * 1_000_000_000:
                    raise ValueError('Echo timing is invalid or too long.')
                return width


def clear_events(request):
    # Bound the drain even if a disconnected/noisy Echo keeps generating edges.
    for _ in range(4):
        if not request.wait_edge_events(timeout=0):
            return
        request.read_edge_events()
    if request.wait_edge_events(timeout=0):
        raise ValueError('Echo is generating continuous edges; check wiring.')


def measure(request, low, high, rising, falling, sleep=time.sleep,
            nano_clock=time.monotonic_ns):
    clear_events(request)
    if request.get_value(ECHO) == high:
        raise ValueError('Echo is already HIGH before triggering; check wiring or sensor state.')
    after_ns = nano_clock()
    try:
        request.set_value(TRIG, high)
        sleep(0.00001)
    finally:
        request.set_value(TRIG, low)
    width = wait_pulse(request, after_ns, rising, falling)
    return distance_cm(width)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--interval', type=float, default=0.5,
                        help='Seconds between attempts, at least 0.06 (default: 0.5).')
    args = parser.parse_args()
    if not 1 <= args.samples <= 100 or not math.isfinite(args.interval) or not 0.06 <= args.interval <= 5:
        parser.error('Use 1-100 samples and a finite interval between 0.06 and 5 seconds.')
    try:
        import gpiod
        from gpiod.line import Direction, Value, Edge, Clock, Bias
        with gpiod.Chip('/dev/gpiochip0') as chip:
            if chip.get_info().label != '1c20800.pinctrl':
                raise RuntimeError('Unexpected GPIO controller; check the Orange Pi pin mapping.')
        config = {
            TRIG: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
            ECHO: gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH,
                                     event_clock=Clock.MONOTONIC, bias=Bias.DISABLED),
        }
        valid = 0
        with gpiod.request_lines('/dev/gpiochip0', consumer='guidebot-hcsr04-test',
                                 config=config, event_buffer_size=16) as request:
            try:
                print('HC-SR04: TRIG physical 29, divided ECHO physical 31. Ctrl+C stops.', flush=True)
                print('Aim at a flat target; compare readings with a ruler.', flush=True)
                time.sleep(0.1)
                for index in range(args.samples):
                    try:
                        cm = measure(request, Value.INACTIVE, Value.ACTIVE,
                                     gpiod.EdgeEvent.Type.RISING_EDGE,
                                     gpiod.EdgeEvent.Type.FALLING_EDGE)
                        print(f'{index + 1:02d}: {cm:.1f} cm', flush=True)
                        valid += 1
                    except (TimeoutError, ValueError) as error:
                        print(f'{index + 1:02d}: NO VALID READING - {error}', flush=True)
                    if index + 1 < args.samples:
                        time.sleep(args.interval)
            finally:
                request.set_value(TRIG, Value.INACTIVE)
        print(f'Finished: {valid}/{args.samples} valid readings. Confirm accuracy against a ruler.')
        return 0 if valid else 2
    except KeyboardInterrupt:
        print('\nStopped.')
        return 0
    except (OSError, RuntimeError, ImportError, AttributeError) as error:
        print(f'Test stopped: {error}')
        print('Check wiring, GPIO ownership, and python3-libgpiod 2.x before retrying.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
