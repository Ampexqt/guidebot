import ast
from pathlib import Path
import unittest


class SourceCompatibilityTests(unittest.TestCase):
    def test_project_sources_parse_with_python_313_grammar(self):
        root = Path(__file__).resolve().parents[1]
        sources = [root / "run_guidebot.py"]
        for folder in ("guidebot", "tests"):
            sources.extend((root / folder).rglob("*.py"))
        for path in sources:
            with self.subTest(path=str(path.relative_to(root))):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 13))
