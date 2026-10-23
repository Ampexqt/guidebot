import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from guidebot.diagnostics import collect_interfaces, main


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dev = self.root / "dev"
        self.sys = self.root / "sys"
        self.dev.mkdir()
        self.sys.mkdir()

    def collect(self):
        return collect_interfaces(dev_root=self.dev, sys_root=self.sys, system="Linux")

    def test_non_linux_reports_unsupported_without_inspecting_paths(self):
        with patch.object(Path, "iterdir", side_effect=AssertionError("must not inspect Linux paths")):
            report = collect_interfaces(system="Windows")
        self.assertFalse(report["supported"])
        self.assertEqual(report["device_nodes"], [])

    def test_detects_adapter_controller_device_and_device_node_metadata(self):
        adapter = self.sys / "class/i2c-adapter/i2c-2"
        adapter.mkdir(parents=True)
        (adapter / "name").write_text("Fixture I2C adapter", encoding="utf-8")
        (self.sys / "class/spi_master/spi1").mkdir(parents=True)
        (self.sys / "bus/spi/devices/spi1.0").mkdir(parents=True)
        for name in ("i2c-2", "spidev1.0", "i2c-wrong", "spidevbad"):
            (self.dev / name).touch()
        report = self.collect()
        self.assertEqual(report["i2c_adapters"], [{"name": "i2c-2", "description": "Fixture I2C adapter"}])
        self.assertEqual(report["spi_controllers"], ["spi1"])
        self.assertEqual(report["spi_devices"], ["spi1.0"])
        self.assertEqual(len(report["device_nodes"]), 2)
        # Fixture files must not be misrepresented as real character devices.
        self.assertFalse(any(item["character_device"] for item in report["device_nodes"]))
        self.assertTrue(report["passive_only"])

    def test_i2c_dev_fallback_and_no_duplicate_adapters(self):
        for kind in ("i2c-adapter", "i2c-dev"):
            (self.sys / f"class/{kind}/i2c-0").mkdir(parents=True)
        report = self.collect()
        self.assertEqual(len(report["i2c_adapters"]), 1)

    def test_missing_interfaces_are_explained(self):
        report = self.collect()
        self.assertEqual(report["i2c_adapters"], [])
        self.assertGreaterEqual(len(report["warnings"]), 3)

    def test_device_nodes_are_never_opened(self):
        (self.dev / "i2c-0").touch()
        (self.dev / "spidev0.0").touch()
        original = Path.open
        def safe_open(path, *args, **kwargs):
            self.assertNotEqual(path.parent, self.dev, "A device node must never be opened")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", safe_open):
            report = self.collect()
        self.assertEqual(len(report["device_nodes"]), 2)

    def test_permission_errors_do_not_crash_inventory(self):
        with patch.object(Path, "iterdir", side_effect=PermissionError("test permission error")):
            report = self.collect()
        self.assertTrue(any("Cannot inspect" in text for text in report["warnings"]))

    def test_json_cli_and_error_exit_code(self):
        output = io.StringIO()
        with patch("guidebot.diagnostics.collect_interfaces", return_value=self.collect()):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--json"]), 0)
        self.assertTrue(json.loads(output.getvalue())["passive_only"])
        report = self.collect()
        report["warnings"].append("Cannot inspect test fixture")
        with patch("guidebot.diagnostics.collect_interfaces", return_value=report):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([]), 1)
