"""Integrated 240x320 Orange Pi frontend: python3 -m guidebot.robot --help."""

import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import signal
import time

from .database import CampusDatabase, DEFAULT_DATABASE

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION = ROOT / 'tools' / 'tft_touch_calibration.json'
GREETING = 'Hello. I am Guide Bot, your campus information assistant. Please tap the screen to choose a destination.'
DETECT_CM = 45
REARM_CM = 50
GREETING_COOLDOWN = 15


def load_calibration(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if (data.get('version'), data.get('width'), data.get('height'), data.get('madctl'),
            data.get('raw_divisor')) != (1, 240, 320, 72, 4095):
        raise ValueError('Calibration must match the tested 240x320 portrait orientation.')
    coefficients = data.get('coefficients')
    if (not isinstance(coefficients, list) or len(coefficients) != 2
            or any(not isinstance(row, list) or len(row) != 3 for row in coefficients)
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for row in coefficients for v in row)):
        raise ValueError('Invalid touch transform.')
    return coefficients


class RobotSession:
    """UI policy isolated from GPIO, drawing and speech subprocesses."""
    def __init__(self, database, speech, motion=None):
        self.database, self.speech, self.motion = database, speech, motion
        self.page = 'face'
        self.menu_page = 0
        self.last_message = ''
        self.nearby = False
        self.last_greeting = -math.inf
        self.talking = False
        self.sensor_error = None

    def say(self, text):
        self.speech.say(text)
        self.last_message = text
        self.talking = True

    def tick(self, now, distance, error=None):
        self.talking = self.speech.active
        if self.motion:
            self.motion.update()
        self.sensor_error = error
        # Missing readings do not re-arm greetings. A valid far reading does.
        if distance is None:
            return
        was_nearby = self.nearby
        self.nearby = distance < (REARM_CM if self.nearby else DETECT_CM)
        if (self.nearby and not was_nearby and self.page == 'face'
                and not self.talking and now - self.last_greeting >= GREETING_COOLDOWN):
            self.last_greeting = now
            print(f'Ultrasonic: object detected at {distance:.1f} cm '
                  f'(trigger <{DETECT_CM} cm).', flush=True)
            self.say(f'Object detected at {distance:.0f} centimeters. ' + GREETING)
            if self.motion:
                self.motion.start(0)

    def action(self, action):
        if action == 'menu':
            self.speech.close()
            self.talking = False
            self.page = 'menu'
        elif action == 'home':
            self.speech.close()
            self.talking = False
            self.page = 'face'
        elif action == 'repeat' and self.last_message and not self.talking:
            self.say(self.last_message)
        elif action == 'next':
            self.menu_page = (self.menu_page + 1) % math.ceil(len(self.database.destinations) / 4)
        elif action == 'motors':
            self.page = 'motors'
        elif action.startswith('motor:') and self.motion:
            self.motion.start(int(action.split(':')[1]))
        elif action.startswith('destination:'):
            destination = self.database.get(action.split(':', 1)[1])
            prefix = 'Demo only. These are fictional campus directions. ' if self.database.is_placeholder else ''
            self.page = 'face'
            self.say(prefix + destination.name + '. ' + ' '.join(destination.steps))
            if self.motion:
                self.motion.start(1)


def render(session, now):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (240, 320), '#081223')
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 16)
        small = ImageFont.truetype('DejaVuSans.ttf', 12)
    except OSError:
        font = ImageFont.load_default(size=16)
        small = ImageFont.load_default(size=12)
    buttons = []

    def button(box, label, action, enabled=True):
        draw.rounded_rectangle(box, radius=9, fill='#184968' if enabled else '#25303b')
        words, lines, line = label.split(), [], ''
        for word in words:
            candidate = (line + ' ' + word).strip()
            if draw.textlength(candidate, font=font) > box[2] - box[0] - 12 and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
        y = (box[1] + box[3]) / 2 - len(lines) * 9
        for line in lines:
            draw.text(((box[0] + box[2]) / 2, y), line, anchor='mt', font=font,
                      fill='white' if enabled else '#88929b')
            y += 18
        if enabled:
            buttons.append((box, action))

    if session.page == 'menu':
        draw.text((120, 12), 'Choose a destination', anchor='mt', font=font, fill='white')
        destinations = session.database.destinations[session.menu_page * 4:][:4]
        for i, item in enumerate(destinations):
            button((10, 42 + i * 49, 230, 87 + i * 49), item.name, 'destination:' + item.id)
        if len(session.database.destinations) > 4:
            button((10, 240, 230, 276), 'More destinations', 'next')
        button((10, 282, 111, 318), 'Face', 'home')
        button((119, 282, 230, 318), 'Motors', 'motors')
    elif session.page == 'motors':
        draw.text((120, 12), 'Unloaded motor test', anchor='mt', font=font, fill='white')
        for i, label in enumerate(('Left hand', 'Right hand', 'Left foot', 'Right foot')):
            button((10, 44 + i * 49, 230, 89 + i * 49), f'{i}: {label}', f'motor:{i}',
                   session.motion is not None and not session.motion.active)
        draw.text((120, 250), 'Bench mode required' if session.motion is None else 'One motor at a time',
                  anchor='mt', font=small, fill='white')
        button((10, 280, 230, 318), 'Menu', 'menu')
    else:
        draw.text((120, 12), 'GuideBot', anchor='mt', font=font, fill='white')
        blink = now % 4 < .18
        for x in (67, 173):
            if blink:
                draw.line((x - 20, 125, x + 20, 125), fill='#66edee', width=6)
            else:
                draw.rounded_rectangle((x - 23, 92, x + 23, 145), radius=18, fill='#66edee')
                draw.ellipse((x - 8, 100, x + 2, 110), fill='white')
        if session.talking and int(now * 5) % 2:
            draw.ellipse((91, 174, 149, 214), fill='#66edee')
        else:
            draw.arc((86, 155, 154, 203), 5, 175, fill='#66edee', width=6)
        draw.text((120, 234), 'Tap face for menu', anchor='mt', font=small, fill='white')
        buttons.append(((0, 38, 239, 262), 'menu'))
        button((10, 274, 115, 318), 'Repeat', 'repeat', bool(session.last_message) and not session.talking)
        button((125, 274, 230, 318), 'Menu', 'menu')
    if session.database.is_placeholder:
        draw.text((236, 29), 'DEMO', anchor='rt', font=small, fill='#ffcb66')
    if session.sensor_error:
        draw.ellipse((5, 5, 11, 11), fill='orange')
    return image, buttons


def hit(buttons, point):
    for (x0, y0, x1, y1), action in buttons:
        if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
            return action
    return None


def stop_signal(*_):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--calibration', type=Path, default=CALIBRATION)
    parser.add_argument('--audio-device', default='plughw:CARD=CD002AUDIO,DEV=0')
    parser.add_argument('--speech-amplitude', type=int, choices=range(201), default=100,
                        metavar='0-200', help='eSpeak amplitude: default 100; maximum 200.')
    parser.add_argument('--bench-motion', action='store_true',
                        help='Enable tested 1400-1600 us pulses on UNATTACHED servos only.')
    parser.add_argument('--check', action='store_true', help='Validate data and calibration without opening hardware.')
    parser.add_argument('--preview', type=Path, help='Save the idle face PNG without hardware (requires Pillow).')
    args = parser.parse_args(argv)
    try:
        database = CampusDatabase(args.database)
        coefficients = load_calibration(args.calibration)
        if args.check:
            print(f'Configuration valid: {len(database.destinations)} destinations; demo={database.is_placeholder}.')
            return 0
        from .robot_devices import Speech, ServoDevice, RangeSensor
        if args.preview:
            session = RobotSession(database, Speech(args.audio_device, args.speech_amplitude))
            render(session, 1)[0].save(args.preview)
            return 0
        from PIL import ImageChops
        from tools.tft_touch_calibrate import Hardware, project
        # SIGTERM follows the same cleanup path as Ctrl+C.
        with ExitStack() as stack:
            old_handler = signal.signal(signal.SIGTERM, stop_signal)
            stack.callback(signal.signal, signal.SIGTERM, old_handler)
            speech = Speech(args.audio_device, args.speech_amplitude)
            stack.callback(speech.close)
            motion = ServoDevice() if args.bench_motion else None
            if motion:
                stack.callback(motion.close)
            display = stack.enter_context(Hardware())
            sensor = RangeSensor()
            stack.callback(sensor.close)
            session = RobotSession(database, speech, motion)
            print('GuideBot running. Tap face for menu. Ctrl+C stops.', flush=True)
            print(f'Ultrasonic greeting: below {DETECT_CM} cm; re-arm at {REARM_CM} cm '
                  f'or farther; cooldown {GREETING_COOLDOWN} seconds.', flush=True)
            print('Bench motors enabled.' if motion else 'Motor outputs are not commanded; use --bench-motion for unloaded tests.', flush=True)
            previous = None
            was_pressed = False
            released_at = time.monotonic()
            last_error = None
            while True:
                now = time.monotonic()
                cm, error = sensor.snapshot()
                if error != last_error:
                    print('Sensor: ' + (error or 'recovered'), flush=True)
                    last_error = error
                session.tick(now, cm, error)
                frame, buttons = render(session, now)
                box = ImageChops.difference(previous, frame).getbbox() if previous else None
                if previous is None or box:
                    display.show(frame, box)
                    previous = frame
                pressed = display.pressed()
                if pressed and not was_pressed and now - released_at >= .12:
                    point = project(coefficients, display.raw())
                    if display.pressed():
                        action = hit(buttons, point)
                        if action:
                            session.action(action)
                if was_pressed and not pressed:
                    released_at = now
                was_pressed = pressed
                time.sleep(.035)
    except KeyboardInterrupt:
        print('\nGuideBot stopped; cleanup completed.')
        return 0
    except Exception as error:
        print(f'GuideBot stopped: {error}')
        print('Check device connections. If motor shutdown failed, disconnect servo power.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
