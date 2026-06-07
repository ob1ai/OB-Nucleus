"""Transport layer: auth, retries, rate-limit backoff, error mapping.

Brief references: Section 3 (auth), Section 8 (errors and rate limits).
The token is read from AUDITY_TOKEN (read scope) or AUDITY_WRITE_TOKEN
(write scope, gated). Tokens are never logged or echoed.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

BASE_URL = "https://app.auditynow.com"
MAX_RETRIES = 3

# Human-readable guidance per brief Section 8.
ERROR_HINTS: dict[str, str] = {
    "PAT_MALFORMED": (
        "Token format invalid. The header must be exactly "
        "'Authorization: Bearer aky_<token>'. Check for a doubled Bearer "
        "prefix; regenerate the token if it persists."
    ),
    "PAT_SCOPE_INSUFFICIENT": (
        "The token lacks the write scope. Reads use AUDITY_TOKEN; approved "
        "writes need AUDITY_WRITE_TOKEN (read+write). Reissue if needed."
    ),
    "PAT_ROUTE_NOT_ALLOWED": (
        "This route is not on the PAT allowlist (web research, billing, "
        "admin). Use the Audity web app for that action."
    ),
    "PAT_NOT_SUPPORTED_FOR_ENDPOINT": (
        "PATs cannot manage PATs. Token management is browser session only."
    ),
    "PAT_DISABLED": (
        "The agent API kill switch is off. Contact support@auditynow.com."
    ),
}

STATUS_HINTS: dict[int, str] = {
    401: "Token does not resolve (revoked, expired, or never existed). Issue a fresh token.",
    402: "Insufficient credits for this operation. Check 'ob-nucleus account credits' and top up.",
    404: "Not found, or not owned by this token's user (row level security).",
    409: "Active token cap reached (10 per user). Revoke an old token first.",
    413: "Content too large to analyze. Reduce the input.",
    422: "Missing prerequisite analysis records. Use the synchronous endpoint for the end to end path.",
    429: "Rate limited. The client backs off automatically; if you see this, retries were exhausted.",
    503: "Server unavailable or agent API disabled (PAT_DISABLED).",
}


class AudityError(Exception):
    """API error with status, Audity error code, and a human hint."""

    def __init__(self, status: int, code: str | None, message: str, hint: str = ""):
        self.status = status
        self.code = code
        self.hint = hint
        text = f"HTTP {status}"
        if code:
            text += f" {code}"
        if message:
            text += f": {message}"
        if hint:
            text += f"\nHint: {hint}"
        super().__init__(text)


def _redact(text: str) -> str:
    """Defensive: strip anything token shaped from outbound text."""
    import re

    return re.sub(r"aky_\w+", "aky_<REDACTED>", text)


class AudityClient:
    """Thin httpx wrapper over the Audity agent API.

    One auth path: Authorization: Bearer <token>. Honors 429 Retry-After,
    retries transient 5xx with exponential backoff, and maps error codes
    to actionable messages.
    """

    def __init__(self, token: str | None = None, base_url: str = BASE_URL, timeout: float = 60.0):
        tok = token or os.environ.get("AUDITY_TOKEN")
        if not tok:
            raise AudityError(0, None, "AUDITY_TOKEN is not set in the environment.",
                              "Run: setx AUDITY_TOKEN \"aky_...\" then open a new terminal.")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=timeout,
        )

    @classmethod
    def write_client(cls) -> "AudityClient":
        """Client on the gated write token. Only call from confirmed write paths."""
        tok = os.environ.get("AUDITY_WRITE_TOKEN")
        if not tok:
            raise AudityError(
                0, None,
                "AUDITY_WRITE_TOKEN is not set. This environment is read only.",
                "Writes require the gated write token and explicit approval from Chris.",
            )
        return cls(token=tok)

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, *, params: dict | None = None,
                json: dict | None = None, timeout: float | None = None) -> Any:
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self._client.request(method, path, params=params, json=json,
                                            timeout=timeout)
            except httpx.TimeoutException as exc:
                raise AudityError(0, None, f"Request timed out: {method} {path}",
                                  "Synthesis calls can take 60 to 300 seconds; "
                                  "pass a longer timeout or use the async path.") from exc

            if resp.status_code == 429 and attempt <= MAX_RETRIES:
                retry_after = float(resp.headers.get("Retry-After", "5"))
                time.sleep(min(retry_after, 120))
                continue
            if resp.status_code >= 500 and attempt <= MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue

            if resp.status_code >= 400:
                code, message = self._parse_error(resp)
                hint = ERROR_HINTS.get(code or "", "") or STATUS_HINTS.get(resp.status_code, "")
                raise AudityError(resp.status_code, code, _redact(message), hint)

            if resp.status_code == 204 or not resp.content:
                return {"success": True, "status": resp.status_code}
            return resp.json()

    @staticmethod
    def _parse_error(resp: httpx.Response) -> tuple[str | None, str]:
        try:
            body = resp.json()
        except Exception:
            return None, resp.text[:300]
        code = body.get("code") or body.get("error_code")
        message = body.get("message") or body.get("error") or str(body)[:300]
        return code, message

    def get(self, path: str, **kw) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> Any:
        return self.request("POST", path, **kw)

    def patch(self, path: str, **kw) -> Any:
        return self.request("PATCH", path, **kw)

    def delete(self, path: str, **kw) -> Any:
        return self.request("DELETE", path, **kw)
