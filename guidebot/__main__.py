"""Run with python -m guidebot. There is deliberately no real-hardware switch."""

import argparse
import logging
import math
from pathlib import Path
import sys

from .database import CampusDatabase, DatabaseError, DEFAULT_DATABASE
from .logging_setup import configure_logging


def positive_int(value):
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError("Use a positive step count.")
    return count


def interval_seconds(value):
    interval = float(value)
    if not math.isfinite(interval) or not 0.1 <= interval <= 60:
        raise argparse.ArgumentTypeError("Interval must be between 0.1 and 60 seconds.")
    return interval


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GuideBot hardware-free campus assistant simulator")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="Local campus JSON path")
    parser.add_argument("--log-file", type=Path, help="Override the rotating log file path")
    parser.add_argument("--validate-data", action="store_true", help="Validate JSON and exit without opening a window")
    parser.add_argument("--headless", action="store_true", help="Use the terminal simulator without importing Tkinter")
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--once", action="store_true", help="With --headless, emit one JSON snapshot and exit")
    execution.add_argument("--steps", type=positive_int, help="With --headless, emit N JSON snapshots and exit")
    execution.add_argument("--monitor", action="store_true", help="With --headless, emit JSON until Ctrl+C")
    parser.add_argument("--interval", type=interval_seconds, default=1.0, help="Headless snapshot interval in seconds (default 1)")
    args = parser.parse_args(argv)
    if (args.once or args.steps is not None or args.monitor) and not args.headless:
        parser.error("--once, --steps, and --monitor require --headless")
    if args.validate_data and (args.headless or args.once or args.steps is not None or args.monitor):
        parser.error("Run --validate-data separately from the simulator")
    configure_logging(args.log_file)
    try:
        database = CampusDatabase(args.database)
    except DatabaseError as exc:
        logging.getLogger("guidebot").error("%s", exc)
        print(f"GuideBot cannot start: {exc}", file=sys.stderr)
        return 2
    if args.validate_data:
        print(f"Validated {len(database.destinations)} destinations. Placeholder data: {database.is_placeholder}.")
        return 0
    if args.headless:
        from .headless import run_headless
        try:
            return run_headless(database, once=args.once, steps=args.steps,
                                monitor=args.monitor, interval=args.interval)
        except Exception:
            logging.getLogger("guidebot").exception("Headless simulator failed")
            return 1
    try:
        import tkinter as tk
        from .app import GuideBotApp
    except ImportError as exc:
        print(f"Tkinter is unavailable: {exc}. Install Python with Tcl/Tk support, "
              "or use python -m guidebot --headless.", file=sys.stderr)
        return 3
    root = None
    app = None
    try:
        root = tk.Tk()
        app = GuideBotApp(root, database)
        root.mainloop()
    except tk.TclError:
        logging.getLogger("guidebot").exception("Tk cannot create or use a graphical display")
        print("A usable Tk graphical display is unavailable. On a terminal-only board, "
              "run python3.13 -m guidebot --headless.", file=sys.stderr)
        return 3
    except Exception:
        logging.getLogger("guidebot").exception("GuideBot could not run")
        print("GuideBot stopped after an error. See the terminal or log file for details.", file=sys.stderr)
        return 1
    finally:
        if app is not None:
            app.close()
        elif root is not None:
            root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
