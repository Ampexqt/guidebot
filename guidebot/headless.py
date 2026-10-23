"""Small terminal/JSON frontend. No GUI, physical device access, or worker thread."""

import json
import logging
import shlex
import sys
import time

from .controller import RobotController
from .hardware.simulated import GESTURES, SimulatedServos, SimulatedUltrasonic

logger = logging.getLogger(__name__)
HELP = """Commands (all hardware is SIMULATED):
  list                  List destination IDs
  search WORDS          Search destination names and aliases
  go ID                 Show a route, e.g. go library
  next / previous       Change route step
  back / home           Navigate
  gesture NAME          wave, nod, look, point, neutral
  distance CM / auto    Set a simulated distance or enable automatic readings
  tick SECONDS          Advance simulated time (0 to 60 seconds)
  status / help / quit
Simulation advances on commands. For continuous telemetry, use --headless --monitor.
"""


def snapshot(controller):
    destination = controller.destination
    return {
        "mode": "simulation",
        "page": controller.page.value,
        "state": controller.state,
        "expression": controller.expression,
        "simulated_seconds": round(controller.elapsed, 3),
        "distance_cm": controller.distance_cm,
        "nearby": controller.nearby,
        "servo_angles": dict(controller.servos.angles),
        "gesture": controller.servos.active_gesture,
        "placeholder": controller.database.is_placeholder,
        "destination": destination.name if destination else None,
        "step_number": controller.step_index + 1 if destination else None,
        "step_count": len(destination.steps) if destination else None,
        "instruction": destination.steps[controller.step_index] if destination else None,
        "errors": {"sensor": controller.sensor_error, "motion": controller.motion_error},
    }


class TerminalSession:
    def __init__(self, controller, sensor, output):
        self.controller = controller
        self.sensor = sensor
        self.output = output

    def write(self, value):
        print(value, file=self.output, flush=True)

    def status(self):
        self.write(json.dumps(snapshot(self.controller), ensure_ascii=True))

    def execute(self, line):
        """Execute one command; return False on quit. Caller handles bad input."""
        parts = shlex.split(line)
        if not parts:
            return True
        command, *arguments = parts
        command = command.casefold()
        c = self.controller
        if command in ("quit", "exit") and not arguments:
            return False
        if command == "help" and not arguments:
            self.write(HELP)
        elif command in ("list", "search"):
            if command == "list" and arguments:
                raise ValueError("Use list without arguments.")
            c.show_menu()
            c.search(" ".join(arguments) if command == "search" else "")
            for destination in c.results:
                self.write(f"{destination.id}: {destination.name}")
            if not c.results:
                self.write("No matching destinations.")
        elif command == "go" and len(arguments) == 1:
            c.select(arguments[0])
        elif command == "gesture" and len(arguments) == 1:
            if arguments[0] not in GESTURES:
                raise ValueError("Choose wave, nod, look, point, or neutral.")
            c.gesture(arguments[0])
        elif command == "distance" and len(arguments) == 1:
            if arguments[0].casefold() == "auto":
                self.sensor.automatic = True
            else:
                self.sensor.set_manual_cm(float(arguments[0]))
                self.sensor.automatic = False
            c.tick(0)
        elif command == "tick" and len(arguments) == 1:
            import math
            elapsed = float(arguments[0])
            if not math.isfinite(elapsed) or not 0 <= elapsed <= 60:
                raise ValueError("tick accepts a finite duration from 0 to 60 seconds.")
            c.tick(elapsed)
        elif command in ("next", "previous", "back", "home", "status") and not arguments:
            actions = {"next": lambda: c.change_step(1), "previous": lambda: c.change_step(-1),
                       "back": c.back, "home": c.home, "status": lambda: None}
            actions[command]()
        else:
            raise ValueError("Unknown command or arguments. Type help.")
        if command not in ("help", "list", "search"):
            self.status()
        return True


def run_headless(database, *, once=False, steps=None, monitor=False, interval=1.0,
                 input_stream=None, output=None):
    """Run a console or constant-memory JSON monitor, always with simulated devices."""
    output = sys.stdout if output is None else output
    input_stream = sys.stdin if input_stream is None else input_stream
    sensor = SimulatedUltrasonic()
    controller = RobotController(database, SimulatedServos(), sensor)
    session = TerminalSession(controller, sensor, output)
    try:
        if once or steps is not None or monitor:
            count = 1 if once else steps
            emitted = 0
            previous = time.monotonic()
            controller.tick(0)
            while count is None or emitted < count:
                if emitted:
                    time.sleep(interval)
                    now = time.monotonic()
                    controller.tick(now - previous)
                    previous = now
                session.status()
                emitted += 1
            return 0
        session.write("Hello! I'm GuideBot! [SIMULATION / NO HARDWARE]")
        session.write(database.notice)
        session.write(HELP)
        controller.tick(0)
        previous = time.monotonic()
        while True:
            if input_stream.isatty():
                print("guidebot> ", end="", file=output, flush=True)
            line = input_stream.readline()
            if not line:
                return 0
            now = time.monotonic()
            controller.tick(now - previous)
            previous = now
            try:
                if not session.execute(line):
                    return 0
            except (ValueError, OSError, RuntimeError) as exc:
                logger.warning("Terminal command failed: %s", exc)
                session.write(f"Error: {exc}")
    except KeyboardInterrupt:
        return 0
    except BrokenPipeError:
        return 0
    finally:
        controller.close()
