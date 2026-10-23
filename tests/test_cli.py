import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from guidebot.__main__ import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / "logs" / "guidebot.log"
        # Close file handlers before TemporaryDirectory cleanup on Windows.
        self.addCleanup(self._close_log_handlers)

    @staticmethod
    def _close_log_handlers():
        import logging
        logger = logging.getLogger("guidebot")
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def test_validate_data_exits_successfully_and_writes_log(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--validate-data", "--log-file", str(self.log)])
        self.assertEqual(result, 0)
        self.assertIn("Validated 4", output.getvalue())
        self.assertTrue(self.log.exists())

    def test_missing_database_returns_error_exit_code(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = main(["--database", str(Path(self.temp.name) / "missing.json"),
                           "--validate-data", "--log-file", str(self.log)])
        self.assertEqual(result, 2)
        self.assertIn("cannot start", output.getvalue())

    def test_headless_snapshot_cli(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--headless", "--once", "--log-file", str(self.log)])
        self.assertEqual(result, 0)
        self.assertTrue(json.loads(output.getvalue())["placeholder"])

    def test_invalid_execution_options_are_rejected(self):
        for arguments in (["--once"], ["--headless", "--steps", "0"],
                          ["--headless", "--interval", "nan"], ["--headless", "--interval", "0"],
                          ["--headless", "--once", "--monitor"], ["--headless", "--validate-data"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(arguments)
                self.assertEqual(error.exception.code, 2)
