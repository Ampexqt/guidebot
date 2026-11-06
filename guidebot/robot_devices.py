"""Orange Pi adapters. Hardware dependencies are imported only when opened."""

import subprocess
import threading
import time

from tools.servo_sequence_test import PCA9685, PULSES_US


class Speech:
    def __init__(self, device):
        self.device = device
        self.children = []

    @property
    def active(self):
        if not self.children:
            return False
        codes = [child.poll() for child in self.children]
        if all(code is not None for code in codes):
            self.children = []
            if any(codes):
                raise RuntimeError('Speech playback failed; check the USB audio device.')
            return False
        return True

    def say(self, text):
        self.close()
        # No shell: route generated WAV data directly to the named USB device.
        source = subprocess.Popen(['espeak-ng', '-v', 'en-us', '-s', '140',
                                   '--stdout', text], stdout=subprocess.PIPE)
        self.children = [source]
        try:
            player = subprocess.Popen(['aplay', '-q', '-D', self.device], stdin=source.stdout)
            self.children.append(player)
        except BaseException:
            self.close()
            raise
        finally:
            source.stdout.close()

    def close(self):
        children, self.children = self.children, []
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


class BenchMotion:
    """Nonblocking small pulses; never drive two unloaded servos together."""
    def __init__(self, controller, clock=time.monotonic):
        self.controller, self.clock = controller, clock
        self.channel = None
        self.index = 0
        self.deadline = 0

    @property
    def active(self):
        return self.channel is not None

    def start(self, channel):
        if self.active:
            return
        if channel not in range(4):
            raise ValueError('Expected servo channel 0-3.')
        self.channel, self.index = channel, 0
        self.deadline = self.clock()

    def update(self):
        if not self.active or self.clock() < self.deadline:
            return
        if self.index == len(PULSES_US):
            self.controller.off(self.channel)
            self.channel = None
            return
        self.controller.pulse(self.channel, PULSES_US[self.index])
        self.index += 1
        self.deadline = self.clock() + 1

    def close(self):
        self.channel = None
        self.controller.off_all()


class ServoDevice(BenchMotion):
    def __init__(self):
        from smbus import SMBus
        self.bus = SMBus(0)
        controller = PCA9685(self.bus)
        try:
            controller.configure()
        except BaseException:
            try:
                controller.off_all()
            finally:
                self.bus.close()
            raise
        super().__init__(controller)

    def close(self):
        try:
            super().close()
        finally:
            self.bus.close()


class RangeSensor:
    """One worker exclusively owns the GPIO request; UI reads a locked snapshot."""
    def __init__(self):
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.sample = (None, 'Starting sensor', 0)
        self.thread = threading.Thread(target=self._run, name='guidebot-range', daemon=True)
        self.thread.start()

    def snapshot(self):
        with self.lock:
            cm, error, stamp = self.sample
        if time.monotonic() - stamp > 2:
            return None, error or 'Sensor reading stale'
        return cm, error

    def _publish(self, cm, error):
        with self.lock:
            self.sample = (cm, error, time.monotonic())

    def _run(self):
        try:
            import gpiod
            from gpiod.line import Direction, Value, Edge, Clock, Bias
            from tools.ultrasonic_test import measure, TRIG, ECHO
            with gpiod.Chip('/dev/gpiochip0') as chip:
                if chip.get_info().label != '1c20800.pinctrl':
                    raise RuntimeError('Unexpected GPIO controller')
            config = {
                TRIG: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                ECHO: gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH,
                                         event_clock=Clock.MONOTONIC, bias=Bias.DISABLED)}
            with gpiod.request_lines('/dev/gpiochip0', consumer='guidebot-range',
                                     config=config, event_buffer_size=16) as request:
                try:
                    while not self.stop.is_set():
                        try:
                            cm = measure(request, Value.INACTIVE, Value.ACTIVE,
                                         gpiod.EdgeEvent.Type.RISING_EDGE,
                                         gpiod.EdgeEvent.Type.FALLING_EDGE)
                            self._publish(cm, None)
                        except (TimeoutError, ValueError) as error:
                            self._publish(None, str(error))
                        self.stop.wait(0.3)
                finally:
                    request.set_value(TRIG, Value.INACTIVE)
        except Exception as error:
            self._publish(None, str(error))

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Range worker did not stop.')
