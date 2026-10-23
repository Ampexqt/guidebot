import copy
import json
from pathlib import Path
import tempfile
import unittest

from guidebot.database import CampusDatabase, DatabaseError, DEFAULT_DATABASE


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = CampusDatabase(DEFAULT_DATABASE)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def load_modified(self, modify):
        raw = copy.deepcopy(json.loads(DEFAULT_DATABASE.read_text(encoding="utf-8")))
        modify(raw)
        path = Path(self.temp.name) / "campus.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return CampusDatabase(path)

    def test_required_sample_destinations_are_labelled_placeholders(self):
        self.assertTrue(self.db.is_placeholder)
        self.assertIn("placeholders", self.db.notice)
        self.assertEqual({d.name for d in self.db.destinations},
                         {"Library", "Registrar", "Computer Laboratory", "Guidance Office"})
        for item in self.db.destinations:
            self.assertGreaterEqual(len(item.steps), 2)

    def test_search_ignores_case_and_outer_whitespace(self):
        self.assertEqual(self.db.search("  LiBrArY  ")[0].id, "library")

    def test_searches_aliases(self):
        for query, identifier in (("books", "library"), ("transcript", "registrar"),
                                  ("ICT", "computer-laboratory"), ("counselling", "guidance-office")):
            with self.subTest(query=query):
                self.assertEqual(self.db.search(query)[0].id, identifier)

    def test_multiword_search_and_no_results(self):
        self.assertEqual(self.db.search("computer programming")[0].id, "computer-laboratory")
        self.assertEqual(self.db.search("unlisted place"), ())
        self.assertEqual(len(self.db.search("")), 4)

    def test_unknown_id_raises_useful_error(self):
        with self.assertRaisesRegex(DatabaseError, "Unknown destination"):
            self.db.get("missing")

    def test_invalid_database_fields_rejected(self):
        cases = {
            "schema": lambda raw: raw.update(schema_version=2),
            "boolean schema": lambda raw: raw.update(schema_version=True),
            "placeholder": lambda raw: raw.update(is_placeholder="yes"),
            "empty destinations": lambda raw: raw.update(destinations=[]),
            "empty steps": lambda raw: raw["destinations"][0].update(steps=[]),
            "invalid step": lambda raw: raw["destinations"][0].update(steps=[42]),
            "blank name": lambda raw: raw["destinations"][0].update(name="  "),
            "duplicate id": lambda raw: raw["destinations"].append(raw["destinations"][0]),
            "invalid alias": lambda raw: raw["destinations"][0].update(aliases=[None]),
        }
        for name, modify in cases.items():
            with self.subTest(name=name), self.assertRaises(DatabaseError):
                self.load_modified(modify)

    def test_missing_or_malformed_file(self):
        path = Path(self.temp.name) / "bad.json"
        with self.assertRaisesRegex(DatabaseError, "Cannot read"):
            CampusDatabase(path)
        path.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(DatabaseError):
            CampusDatabase(path)
        path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(DatabaseError, "JSON object"):
            CampusDatabase(path)
