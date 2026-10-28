#!/usr/bin/env python3
"""Standalone Orange Pi One display/touch check; does not control motors.

Display: SPI0 CS0, DC=PA2, RESET=PC7, 240x320 ILI9341-compatible.
Touch: CLK=PA1, CS=PA3, DIN=PA0, DO=PC4, IRQ=PA6 (software SPI).
Requires Debian python3-spidev, python3-libgpiod (2.x), python3-pil.
"""

import argparse
import json
import math
from pathlib import Path
import statistics
import time

WIDTH, HEIGHT = 240, 320
TARGETS = [(24, 32), (215, 32), (215, 287), (24, 287), (120, 160)]
CHECKS = [(60, 80), (180, 240), (120, 160)]


def solve(matrix, values):
    rows = [list(row) + [value] for row, value in zip(matrix, values)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda i: abs(rows[i][column]))
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        if abs(divisor) < 1e-10:
            raise ValueError("Touch samples do not define a usable calibration.")
        rows[column] = [v / divisor for v in rows[column]]
        for i in range(3):
            if i != column:
                factor = rows[i][column]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[column])]
    return [rows[i][3] for i in range(3)]


def fit(raw, targets):
    # Normalize raw ADC readings to keep the small linear system well conditioned.
    vectors = [(x / 4095, y / 4095, 1.0) for x, y in raw]
    matrix = [[sum(v[i] * v[j] for v in vectors) for j in range(3)]
              for i in range(3)]
    return [solve(matrix, [sum(v[i] * p[axis] for v, p in zip(vectors, targets))
                           for i in range(3)]) for axis in range(2)]


def project(coefficients, raw):
    v = (raw[0] / 4095, raw[1] / 4095, 1.0)
    return tuple(sum(a * b for a, b in zip(row, v)) for row in coefficients)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Hardware:
    DC, RESET = 2, 71
    CLK, CS, DIN, DOUT, IRQ = 1, 3, 0, 68, 6

    def __enter__(self):
        import gpiod
        from gpiod.line import Direction, Value, Bias
        import spidev
        self.low, self.high = Value.INACTIVE, Value.ACTIVE
        config = {}
        for line in (self.DC, self.RESET, self.CLK, self.CS, self.DIN):
            config[line] = gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=self.high if line in (self.RESET, self.CS) else self.low)
        config[self.DOUT] = gpiod.LineSettings(direction=Direction.INPUT)
        config[self.IRQ] = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)
        self.pins = None
        self.spi = None
        try:
            with gpiod.Chip('/dev/gpiochip0') as chip:
                if chip.get_info().label != '1c20800.pinctrl':
                    raise RuntimeError('Unexpected GPIO controller. Stop and check the pin mapping.')
            self.pins = gpiod.request_lines('/dev/gpiochip0', consumer='guidebot-calibration',
                                            config=config)
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 1_000_000
            self.spi.mode = 0
            self.set(self.RESET, False)
            time.sleep(0.1)
            self.set(self.RESET, True)
            time.sleep(0.15)
            self.command(0x01)
            time.sleep(0.15)
            # ILI9341 register setup, matching the successful color test.
            setup = [(0xCF, [0, 0xC1, 0x30]), (0xED, [0x64, 3, 0x12, 0x81]),
                     (0xE8, [0x85, 0, 0x78]), (0xCB, [0x39, 0x2C, 0, 0x34, 2]),
                     (0xF7, [0x20]), (0xEA, [0, 0]), (0xC0, [0x23]),
                     (0xC1, [0x10]), (0xC5, [0x3E, 0x28]), (0xC7, [0x86]),
                     (0x36, [0x48]), (0x3A, [0x55]), (0xB1, [0, 0x18]),
                     (0xB6, [8, 0x82, 0x27])]
            for number, data in setup:
                self.command(number, data)
            self.command(0x11)
            time.sleep(0.15)
            self.command(0x29)
            time.sleep(0.1)
            self.adc(0x90)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        try:
            if self.spi is not None:
                self.spi.close()
        finally:
            if self.pins is not None:
                self.pins.release()

    def set(self, line, high):
        self.pins.set_value(line, self.high if high else self.low)

    def command(self, number, data=()):
        self.set(self.DC, False)
        self.spi.writebytes([number])
        if data:
            self.set(self.DC, True)
            self.spi.writebytes(list(data))

    def show(self, image, box=None):
        x0, y0, x1, y1 = box or (0, 0, WIDTH, HEIGHT)
        self.command(0x2A, [x0 >> 8, x0 & 255, (x1 - 1) >> 8, (x1 - 1) & 255])
        self.command(0x2B, [y0 >> 8, y0 & 255, (y1 - 1) >> 8, (y1 - 1) & 255])
        self.command(0x2C)
        self.set(self.DC, True)
        pixels = image.load()
        for y in range(y0, y1):
            row = bytearray()
            for x in range(x0, x1):
                r, g, b = pixels[x, y]
                value = ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)
                row.extend((value >> 8, value & 255))
            self.spi.writebytes2(row)

    def pressed(self):
        return self.pins.get_value(self.IRQ) == self.low

    def adc(self, command):
        result = 0
        self.set(self.CLK, False)
        self.set(self.CS, False)
        try:
            for byte in (command, 0, 0):
                for bit in range(7, -1, -1):
                    self.set(self.CLK, False)
                    self.set(self.DIN, bool(byte & (1 << bit)))
                    self.set(self.CLK, True)
                    result = (result << 1) | (self.pins.get_value(self.DOUT) == self.high)
                    self.set(self.CLK, False)
        finally:
            self.set(self.CS, True)
        return (result >> 3) & 4095

    def raw(self):
        self.adc(0xD0)
        x = statistics.median(self.adc(0xD0) for _ in range(3))
        self.adc(0x90)
        y = statistics.median(self.adc(0x90) for _ in range(3))
        return (x, y)

    def release(self):
        while True:
            while self.pressed():
                time.sleep(0.02)
            time.sleep(0.08)
            if not self.pressed():
                return

    def capture(self):
        self.release()
        while not self.pressed():
            time.sleep(0.02)
        samples = []
        start = time.monotonic()
        while self.pressed() and time.monotonic() - start < 2:
            point = self.raw()
            if self.pressed():
                samples.append(point)
            time.sleep(0.025)
        print('Lift your finger.', flush=True)
        self.release()
        if len(samples) < 3:
            raise ValueError('Hold the target a little longer (about one second).')
        point = tuple(statistics.median(p[i] for p in samples) for i in range(2))
        if any(statistics.median(abs(p[i] - point[i]) for p in samples) > 100
               for i in range(2)):
            raise ValueError('Readings moved too much. Hold gently without dragging.')
        if any(v < 30 or v > 4065 for v in point):
            raise ValueError('Readings are near the ADC limit. Check touch wiring.')
        return point


def page(title, footer='Tap cross, hold 1 second, release', target=None):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (WIDTH, HEIGHT), (8, 18, 35))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((7, 6), title, font=font, fill='white')
    draw.text((7, 305), footer, font=font, fill='white')
    if target is not None:
        x, y = target
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), outline='red', width=2)
        draw.line((x - 14, y, x + 14, y), fill='white')
        draw.line((x, y - 14, x, y + 14), fill='white')
    return image


def main(output):
    from PIL import ImageDraw
    print('Follow targets on the TFT itself, even if you held it differently before.', flush=True)
    print('Touch with a rounded plastic stylus or gentle fingertip. Ctrl+C stops.', flush=True)
    with Hardware() as hw:
        samples = []
        for i, target in enumerate(TARGETS, 1):
            hw.show(page(f'GuideBot: calibration {i}/5', target=target))
            print(f'Tap target {i}/5 at screen pixel {target}.', flush=True)
            while True:
                try:
                    point = hw.capture()
                    samples.append(point)
                    print(f'Captured raw {point}', flush=True)
                    break
                except ValueError as error:
                    print(f'Retry this target: {error}', flush=True)
        coefficients = fit(samples, TARGETS)
        errors = [distance(project(coefficients, p), t) for p, t in zip(samples, TARGETS)]
        rms = math.sqrt(sum(e * e for e in errors) / len(errors))
        print(f'Calibration fit: RMS={rms:.1f}px; maximum={max(errors):.1f}px', flush=True)
        if rms > 12 or max(errors) > 20:
            raise ValueError('Calibration inconsistent. Rerun and tap each displayed cross precisely.')
        checks = []
        for i, target in enumerate(CHECKS, 1):
            hw.show(page(f'GuideBot: verify {i}/3', target=target))
            for attempt in range(3):
                print(f'Verify target {i}/3 at {target}.', flush=True)
                try:
                    raw = hw.capture()
                except ValueError as error:
                    print(f'Retry: {error}', flush=True)
                    continue
                mapped = project(coefficients, raw)
                error = distance(mapped, target)
                print(f'Mapped ({mapped[0]:.1f}, {mapped[1]:.1f}); error={error:.1f}px', flush=True)
                if error <= 20:
                    checks.append({'target': target, 'raw': raw, 'error_pixels': error})
                    break
                print('Missed target. Try the exact cross center again.', flush=True)
            else:
                raise ValueError('Verification failed. Calibration was not saved; rerun the test.')
        result = {'version': 1, 'width': WIDTH, 'height': HEIGHT, 'madctl': 0x48,
                  'raw_divisor': 4095, 'transform': 'pixel = ax*raw_x/4095 + ay*raw_y/4095 + c',
                  'coefficients': coefficients, 'samples': samples, 'targets': TARGETS,
                  'fit_rms_pixels': rms, 'verification': checks}
        temporary = output.with_name(output.name + '.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
        print(f'PASS: calibration and three checks completed. Saved {output}', flush=True)
        print('Now touch anywhere: a yellow dot should follow. Ctrl+C stops.', flush=True)
        background = page('GuideBot: touch check', 'Yellow dot follows touch. Ctrl+C exits')
        hw.show(background)
        previous = None
        while True:
            if hw.pressed():
                raw = hw.raw()
                if not hw.pressed():
                    continue
                x, y = project(coefficients, raw)
                point = (max(0, min(WIDTH - 1, round(x))),
                         max(0, min(HEIGHT - 1, round(y))))
                image = background.copy()
                ImageDraw.Draw(image).ellipse((point[0] - 4, point[1] - 4,
                                              point[0] + 4, point[1] + 4), fill='yellow')
                if previous is None:
                    box = None
                else:
                    box = (max(0, min(previous[0], point[0]) - 5),
                           max(0, min(previous[1], point[1]) - 5),
                           min(WIDTH, max(previous[0], point[0]) + 6),
                           min(HEIGHT, max(previous[1], point[1]) + 6))
                hw.show(image, box)
                previous = point
                print(f'Pixel X={x:.0f}, Y={y:.0f}', flush=True)
            time.sleep(0.04)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().with_name('tft_touch_calibration.json'))
    args = parser.parse_args()
    try:
        main(args.output)
    except KeyboardInterrupt:
        print('\nStopped. Any successfully saved calibration remains available.')
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f'Test stopped: {error}', flush=True)
        raise SystemExit(1)
