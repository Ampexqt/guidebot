import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def configure_logging(log_file: Path | None = None) -> Path | None:
    root = logging.getLogger("guidebot")
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
    if log_file is None:
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
        log_file = base / "GuideBot" / "logs" / "guidebot.log"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=500_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.info("Log file: %s", log_file)
        return log_file
    except OSError:
        root.exception("Cannot create log file; console logging remains available")
        return None
