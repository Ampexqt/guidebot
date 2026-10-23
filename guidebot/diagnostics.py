"""Passive Linux interface inventory. Never opens /dev nodes or transmits bus data."""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import stat


def collect_interfaces(*, dev_root=Path("/dev"), sys_root=Path("/sys"), system=None):
    system = platform.system() if system is None else system
    report = {
        "system": system,
        "python": platform.python_version(),
        "supported": system == "Linux",
        "passive_only": True,
        "i2c_adapters": [],
        "spi_controllers": [],
        "spi_devices": [],
        "device_nodes": [],
        "warnings": [],
        "limitations": "Inventory only. Does not identify attached chips, validate wiring, "
                       "verify bus transactions, or activate motors.",
    }
    if system != "Linux":
        report["warnings"].append("Linux interface detection is unavailable on this platform.")
        return report
    dev_root, sys_root = Path(dev_root), Path(sys_root)

    def entries(directory, pattern):
        try:
            return sorted((path for path in directory.iterdir() if re.fullmatch(pattern, path.name)),
                          key=lambda path: path.name)
        except FileNotFoundError:
            return []
        except OSError as exc:
            report["warnings"].append(f"Cannot inspect {directory}: {exc}")
            return []

    def label(path):
        try:
            # This is a kernel metadata file under sysfs, never a device node.
            with (path / "name").open(encoding="utf-8", errors="replace") as stream:
                return stream.read(256).strip()
        except FileNotFoundError:
            return None
        except OSError as exc:
            report["warnings"].append(f"Cannot read metadata for {path.name}: {exc}")
            return None

    adapters = {}
    for directory in (sys_root / "class/i2c-adapter", sys_root / "class/i2c-dev"):
        for path in entries(directory, r"i2c-\d+"):
            adapters.setdefault(path.name, {"name": path.name, "description": label(path)})
    report["i2c_adapters"] = list(adapters.values())
    report["spi_controllers"] = [path.name for path in entries(sys_root / "class/spi_master", r"spi\d+")]
    report["spi_devices"] = [path.name for path in entries(sys_root / "bus/spi/devices", r"spi\d+\.\d+")]
    for path in entries(dev_root, r"(?:i2c-\d+|spidev\d+\.\d+)"):
        try:
            metadata = path.stat()
        except OSError as exc:
            report["warnings"].append(f"Cannot stat {path}: {exc}")
            continue
        report["device_nodes"].append({
            "path": str(path),
            "character_device": stat.S_ISCHR(metadata.st_mode),
            "read_permission": os.access(path, os.R_OK),
            "write_permission": os.access(path, os.W_OK),
        })
    if not report["i2c_adapters"]:
        report["warnings"].append("No I2C adapters visible in sysfs; this does not prove the board lacks I2C.")
    if not report["spi_controllers"]:
        report["warnings"].append("No SPI controllers visible in sysfs; check the board's verified Armbian configuration later.")
    if not report["device_nodes"]:
        report["warnings"].append("No I2C/spidev userspace nodes visible; a kernel driver may own an interface instead.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="GuideBot passive I2C/SPI inventory (no bus traffic or motors)")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report")
    args = parser.parse_args(argv)
    report = collect_interfaces()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"GuideBot passive interface inventory / {report['system']} / Python {report['python']}")
        print(report["limitations"])
        for key in ("i2c_adapters", "spi_controllers", "spi_devices", "device_nodes"):
            print(f"{key}: {json.dumps(report[key])}")
        for warning in report["warnings"]:
            print(f"NOTE: {warning}")
    # 0 = inventory completed; it does not mean hardware is connected or tested.
    return 1 if report["supported"] and any(w.startswith("Cannot ") for w in report["warnings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
