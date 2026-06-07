"""Error mapping tests: brief Section 8 codes become actionable messages."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx  # noqa: E402

from ob_nucleus.client import AudityClient, AudityError  # noqa: E402


def _client_returning(status: int, body: dict) -> AudityClient:
    client = AudityClient.__new__(AudityClient)
    client._client = httpx.Client(
        base_url="https://stub.local",
        transport=httpx.MockTransport(lambda req: httpx.Response(status, json=body)))
    return client


class ErrorMappingTests(unittest.TestCase):
    def test_pat_malformed_hint(self):
        c = _client_returning(401, {"code": "PAT_MALFORMED", "message": "bad token"})
        with self.assertRaises(AudityError) as ctx:
            c.get("/api/user/current")
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(ctx.exception.code, "PAT_MALFORMED")
        self.assertIn("doubled Bearer", str(ctx.exception))

    def test_scope_insufficient_hint(self):
        c = _client_returning(403, {"code": "PAT_SCOPE_INSUFFICIENT", "message": "no write"})
        with self.assertRaises(AudityError) as ctx:
            c.post("/api/nucleus/memories", json={})
        self.assertIn("write scope", str(ctx.exception))

    def test_402_insufficient_credits(self):
        c = _client_returning(402, {"message": "insufficient credits"})
        with self.assertRaises(AudityError) as ctx:
            c.post("/api/projects", json={})
        self.assertEqual(ctx.exception.status, 402)
        self.assertIn("credits", str(ctx.exception).lower())

    def test_429_exhausts_retries_then_raises(self):
        attempts = []

        def handler(req):
            attempts.append(1)
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})

        client = AudityClient.__new__(AudityClient)
        client._client = httpx.Client(base_url="https://stub.local",
                                      transport=httpx.MockTransport(handler))
        with self.assertRaises(AudityError) as ctx:
            client.get("/api/projects")
        self.assertEqual(ctx.exception.status, 429)
        self.assertGreater(len(attempts), 3)

    def test_token_redaction_in_errors(self):
        fake = "aky_" + "x" * 16  # built at runtime so secret scanners never flag a literal
        c = _client_returning(400, {"message": f"echo {fake} here"})
        with self.assertRaises(AudityError) as ctx:
            c.get("/api/projects")
        self.assertNotIn(fake, str(ctx.exception))
        self.assertIn("aky_<REDACTED>", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
