"""Deterministic, nonblocking hardware substitutes. No GPIO, I2C, or SPI calls."""

import math
from types import MappingProxyType

from .interfaces import SERVO_NAMES

NEUTRAL = {name: 90.0 for name in SERVO_NAMES}
GESTURES = {
    "wave": [(0.3, {"right_arm": 140}), (0.25, {"right_arm": 65}),
             (0.25, {"right_arm": 140}), (0.25, {"right_arm": 65}), (0.4, NEUTRAL)],
    "nod": [(0.3, {"head_tilt": 110}), (0.3, {"head_tilt": 75}),
            (0.3, {"head_tilt": 110}), (0.4, NEUTRAL)],
    "look": [(0.45, {"head_pan": 55}), (0.7, {"head_pan": 125}), (0.45, NEUTRAL)],
    "point": [(0.4, {"left_arm": 135, "head_pan": 110}),
              (0.8, {"left_arm": 135, "head_pan": 110}), (0.4, NEUTRAL)],
    "neutral": [(0.35, NEUTRAL)],
}


class SimulatedServos:
    def __init__(self):
        self._angles = dict(NEUTRAL)
        self._queue = []
        self._start = dict(NEUTRAL)
        self._elapsed = 0.0
        self.active_gesture = "idle"
        self.closed = False

    @property
    def angles(self):
        return MappingProxyType(self._angles)

    def gesture(self, name: str) -> None:
        if self.closed:
            raise RuntimeError("Servo simulator is closed.")
        if name not in GESTURES:
            raise ValueError(f"Unknown gesture: {name}")
        self._queue = [(duration, {**NEUTRAL, **pose}) for duration, pose in GESTURES[name]]
        self._start = dict(self._angles)
        self._elapsed = 0.0
        self.active_gesture = name

    def update(self, dt: float) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Elapsed time must be finite and nonnegative.")
        while self._queue:
            duration, target = self._queue[0]
            used = min(dt, duration - self._elapsed)
            self._elapsed += used
            dt -= used
            fraction = min(1.0, self._elapsed / duration)
            for name in SERVO_NAMES:
                self._angles[name] = max(0.0, min(180.0,
                    self._start[name] + (target[name] - self._start[name]) * fraction))
            if self._elapsed < duration:
                break
            self._queue.pop(0)
            self._start = dict(self._angles)
            self._elapsed = 0.0
        if not self._queue:
            self.active_gesture = "idle"

    def close(self) -> None:
        self._queue.clear()
        self.active_gesture = "idle"
        self.closed = True


class SimulatedUltrasonic:
    def __init__(self):
        self.automatic = True
        self._manual_cm = 100.0
        self._elapsed = 0.0
        self.closed = False

    def set_manual_cm(self, distance: float) -> None:
        if not math.isfinite(distance) or not 2 <= distance <= 400:
            raise ValueError("Simulated distance must be between 2 and 400 cm.")
        self._manual_cm = float(distance)

    def update(self, dt: float) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Elapsed time must be finite and nonnegative.")
        self._elapsed += dt

    def read_cm(self) -> float:
        if self.closed:
            raise RuntimeError("Sensor simulator is closed.")
        if not self.automatic:
            return self._manual_cm
        return round(80 + 52 * math.sin(self._elapsed * 0.42)
                     + 1.2 * math.sin(self._elapsed * 3), 1)

    def close(self) -> None:
        self.closed = True
