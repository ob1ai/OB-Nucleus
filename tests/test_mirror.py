"""Unit tests for mirror pure functions: scope filter, exclusion list,
duplicate normalization, freshness math, response unwrapping.
No network, no SQLite file, no Supabase. Stdlib unittest, house style.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from ob_nucleus import mirror


class EnvCase(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("OBN_TEST_CLIENT_PREFIXES")
        os.environ.pop("OBN_TEST_CLIENT_PREFIXES", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("OBN_TEST_CLIENT_PREFIXES", None)
        else:
            os.environ["OBN_TEST_CLIENT_PREFIXES"] = self._saved


class TestActiveClients(EnvCase):
    def test_excludes_setup_archived_and_sandbox(self):
        projects = [
            {"id": "1", "clientName": "Athens Foods", "status": "interviews"},
            {"id": "2", "clientName": "Sandbox Rig", "status": "analysis"},
            {"id": "3", "clientName": "New Client", "status": "setup"},
            {"id": "4", "clientName": "Old Client", "status": "archived"},
            {"id": "5", "clientName": "USI Insurance", "status": "analysis"},
        ]
        out = mirror.active_clients(projects)
        self.assertEqual([p["id"] for p in out], ["1", "5"])

    def test_exclusion_list_extends_via_env(self):
        os.environ["OBN_TEST_CLIENT_PREFIXES"] = "sandbox, demo"
        projects = [
            {"id": "1", "clientName": "Demo Corp", "status": "analysis"},
            {"id": "2", "clientName": "Real Corp", "status": "analysis"},
        ]
        out = mirror.active_clients(projects)
        self.assertEqual([p["id"] for p in out], ["2"])

    def test_handles_missing_fields(self):
        projects = [{"id": "1"}, {"id": "2", "status": None, "clientName": None}]
        self.assertEqual(len(mirror.active_clients(projects)), 2)


class TestHelpers(unittest.TestCase):
    def test_normalized_name_collapses_case_and_whitespace(self):
        self.assertEqual(mirror._normalized_name("  Cleveland   CANDY Co "),
                         "cleveland candy")
        self.assertEqual(mirror._normalized_name(None), "")

    def test_normalized_name_catches_live_cleveland_candy_pair(self):
        a = mirror._normalized_name("Cleveland Candy Co.")
        b = mirror._normalized_name("Cleveland Candy Company")
        self.assertEqual(a, b)
        self.assertEqual(a, "cleveland candy")
        self.assertEqual(mirror._normalized_name("Innovatio AI Solutions GmbH"),
                         "innovatio ai solutions")
        self.assertNotEqual(mirror._normalized_name("Inside Small Business"),
                            mirror._normalized_name("Inside Small"))

    def test_hours_since_handles_iso_and_z_suffix(self):
        two_h = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        age = mirror._hours_since(two_h)
        self.assertIsNotNone(age)
        self.assertTrue(1.9 < age < 2.1)
        age_z = mirror._hours_since(two_h.replace("+00:00", "Z"))
        self.assertIsNotNone(age_z)
        self.assertTrue(1.9 < age_z < 2.1)
        self.assertIsNone(mirror._hours_since(None))
        self.assertIsNone(mirror._hours_since("not a timestamp"))

    def test_purge_guard_refuses_empty_set(self):
        self.assertEqual(mirror._purge_stale_projects(("https://x", "k"), []), 0)
        self.assertEqual(
            mirror._purge_stale_projects(("https://x", "k"), [{"name": "no id"}]), 0)

    def test_items_unwraps_known_shapes(self):
        self.assertEqual(mirror._items([1, 2], "x"), [1, 2])
        self.assertEqual(mirror._items({"data": [1]}, "x"), [1])
        self.assertEqual(mirror._items({"projects": [1]}, "projects"), [1])
        self.assertEqual(mirror._items({"nope": 1}, "x"), [])
        self.assertEqual(mirror._items(None, "x"), [])


if __name__ == "__main__":
    unittest.main()
