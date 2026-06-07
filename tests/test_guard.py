"""Write guard tests: writes refuse to fire without the confirm flag.

Run from the repo root: python -m unittest discover tests
No network calls are made; the Audity API is stubbed with httpx.MockTransport.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx  # noqa: E402

from ob_nucleus.api import Audity, DryRun  # noqa: E402
from ob_nucleus.client import AudityClient  # noqa: E402

CALLS: list[str] = []


def _mock_handler(request: httpx.Request) -> httpx.Response:
    CALLS.append(f"{request.method} {request.url.path}")
    if request.url.path == "/api/user/credits":
        return httpx.Response(200, json={"remaining": 50000, "allocated": 50000})
    return httpx.Response(200, json={"ok": True})


def _stub_audity() -> Audity:
    a = Audity.__new__(Audity)
    client = AudityClient.__new__(AudityClient)
    client._client = httpx.Client(base_url="https://stub.local",
                                  transport=httpx.MockTransport(_mock_handler))
    a.client = client
    from ob_nucleus.api import AccountAPI, LeadsAPI, NucleusAPI, ProjectsAPI
    a.account = AccountAPI(client)
    a.projects = ProjectsAPI(client)
    a.leads = LeadsAPI(client)
    a.nucleus = NucleusAPI(client)
    return a


class WriteGuardTests(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        self.a = _stub_audity()

    def tearDown(self):
        self.a.close()

    def test_create_project_without_confirm_is_dry_run(self):
        result = self.a.projects.create("Test Project")
        self.assertIsInstance(result, DryRun)
        self.assertEqual(result.credit_cost, 1000)
        self.assertNotIn("POST /api/projects", CALLS)

    def test_convert_lead_without_confirm_is_dry_run(self):
        result = self.a.leads.convert("lead-123")
        self.assertIsInstance(result, DryRun)
        self.assertEqual(result.credit_cost, 1000)
        self.assertNotIn("POST /api/lead-generation/leads/lead-123/convert", CALLS)

    def test_nucleus_memory_create_without_confirm_is_dry_run(self):
        result = self.a.nucleus.create_memory("Subject", "Content")
        self.assertIsInstance(result, DryRun)
        self.assertNotIn("POST /api/nucleus/memories", CALLS)

    def test_dry_run_reports_credit_position(self):
        result = self.a.projects.create("Test Project")
        self.assertEqual(result.credits_remaining, 50000)
        self.assertIn("DRY RUN", result.note)

    def test_confirmed_write_requires_write_token(self):
        import os
        from ob_nucleus.client import AudityError
        os.environ.pop("AUDITY_WRITE_TOKEN", None)
        with self.assertRaises(AudityError):
            self.a.projects.create("Test Project", confirm=True)
        self.assertNotIn("POST /api/projects", CALLS)


if __name__ == "__main__":
    unittest.main()
