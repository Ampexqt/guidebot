"""UI-independent navigation and robot behavior with injected device interfaces."""

from enum import Enum
import logging
import math

from .database import CampusDatabase
from .hardware.interfaces import DistanceSensor, ServoDriver

logger = logging.getLogger(__name__)


class Page(str, Enum):
    WELCOME = "welcome"
    MENU = "menu"
    DIRECTIONS = "directions"


class RobotController:
    def __init__(self, database: CampusDatabase, servos: ServoDriver, sensor: DistanceSensor):
        self.database = database
        self.servos = servos
        self.sensor = sensor
        self.page = Page.WELCOME
        self.query = ""
        self.destination = None
        self.step_index = 0
        self.distance_cm = None
        self.nearby = False
        self.sensor_error = None
        self.motion_error = None
        self.elapsed = 0.0
        self._last_greeting = -10.0
        self.closed = False

    @property
    def results(self):
        return self.database.search(self.query)

    @property
    def state(self) -> str:
        if self.sensor_error or self.motion_error:
            return "Device error (simulated)"
        if self.servos.active_gesture != "idle":
            return f"Gesture: {self.servos.active_gesture}"
        if self.page == Page.DIRECTIONS:
            return "Giving directions"
        if self.page == Page.MENU:
            return "Finding a destination"
        return "Visitor nearby" if self.nearby else "Ready to welcome"

    @property
    def expression(self) -> str:
        if self.sensor_error or self.motion_error:
            return "concerned"
        if self.servos.active_gesture in ("wave", "nod"):
            return "happy"
        if self.page == Page.DIRECTIONS:
            return "focused"
        return "curious" if self.nearby else "friendly"

    def home(self) -> None:
        self.page = Page.WELCOME
        self.destination = None
        self.step_index = 0
        self.query = ""
        logger.info("Home screen")

    def show_menu(self) -> None:
        self.page = Page.MENU
        logger.info("Campus menu")

    def back(self) -> None:
        if self.page == Page.DIRECTIONS:
            self.show_menu()
        else:
            self.home()

    def search(self, query: str) -> None:
        self.query = query.strip()

    def select(self, identifier: str) -> None:
        destination = self.database.get(identifier)
        self.destination = destination
        self.step_index = 0
        self.page = Page.DIRECTIONS
        try:
            self.gesture("point")
        except Exception:
            # A gesture failure must not hide an otherwise valid campus route.
            # gesture() has already logged the failure and set motion_error.
            pass
        logger.info("Selected destination %s (placeholder=%s)", identifier, self.database.is_placeholder)

    def change_step(self, delta: int) -> None:
        if self.destination is not None:
            self.step_index = max(0, min(len(self.destination.steps) - 1, self.step_index + delta))

    def gesture(self, name: str) -> None:
        try:
            self.servos.gesture(name)
        except Exception as exc:
            self.motion_error = str(exc)
            logger.exception("Gesture failed")
            raise
        self.motion_error = None
        logger.info("Simulated gesture: %s", name)

    def tick(self, dt: float) -> None:
        if self.closed:
            return
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Elapsed time must be finite and nonnegative.")
        self.elapsed += dt
        try:
            self.servos.update(dt)
        except Exception as exc:
            if self.motion_error is None:
                logger.exception("Servo update failed")
            self.motion_error = str(exc)
        try:
            self.sensor.update(dt)
            distance = self.sensor.read_cm()
            if not math.isfinite(distance) or not 2 <= distance <= 400:
                raise ValueError("Distance reading outside 2–400 cm.")
            if self.sensor_error is not None:
                logger.info("Sensor recovered")
            self.sensor_error = None
            self.distance_cm = distance
        except Exception as exc:
            if self.sensor_error is None:
                logger.exception("Distance sensor read failed")
            self.sensor_error = str(exc)
            self.distance_cm = None
        was_nearby = self.nearby
        # A 5 cm hysteresis band prevents repeated greeting at the threshold.
        if self.distance_cm is None:
            self.nearby = False
        elif self.nearby:
            self.nearby = self.distance_cm < 50
        else:
            self.nearby = self.distance_cm < 45
        if (self.nearby and not was_nearby and self.page == Page.WELCOME
                and self.elapsed - self._last_greeting >= 8
                and self.servos.active_gesture == "idle" and self.motion_error is None):
            self._last_greeting = self.elapsed
            try:
                self.gesture("wave")
            except Exception:
                pass  # Already logged; keep navigation and the Tk event loop alive.

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        for device in (self.servos, self.sensor):
            try:
                device.close()
            except Exception:
                logger.exception("Device shutdown failed")
