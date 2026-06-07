"""Resource groups over the PAT allowlist (brief Section 7) with a write guard.

Groups: account, projects, leads, nucleus. Every write is guarded:
default behavior is a dry run that prints the exact request and the
credit position, then makes no call. Passing confirm=True runs the
credit check first and uses the gated write token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import AudityClient, AudityError

CREDIT_COSTS = {
    "createProject": 1000,
    "convertLead": 1000,
    "triggerAuditAnalysis": "varies by depth",
}


@dataclass
class DryRun:
    """The request a write would send. Returned when confirm is False."""

    operation: str
    method: str
    path: str
    body: dict | None
    credit_cost: Any
    credits_remaining: int | None
    note: str = (
        "DRY RUN: no call was made. Re-run with confirm=True (CLI: --confirm) "
        "after explicit approval. Writes use AUDITY_WRITE_TOKEN."
    )

    def to_dict(self) -> dict:
        return {
            "dry_run": True,
            "operation": self.operation,
            "would_send": {"method": self.method, "path": self.path, "body": self.body},
            "credit_cost": self.credit_cost,
            "credits_remaining": self.credits_remaining,
            "note": self.note,
        }


class _Group:
    def __init__(self, client: AudityClient):
        self.c = client


class AccountAPI(_Group):
    def whoami(self) -> dict:
        return self.c.get("/api/user/current")

    def tier(self) -> dict:
        return self.c.get("/api/user/tier")

    def credits(self) -> dict:
        return self.c.get("/api/user/credits")

    def preflight(self) -> dict:
        """Identity, tier, and credits in one shot (brief Phase 3 requirement)."""
        return {"whoami": self.whoami(), "tier": self.tier(), "credits": self.credits()}


class ProjectsAPI(_Group):
    def list(self) -> Any:
        return self.c.get("/api/projects")

    def get(self, project_id: str) -> Any:
        return self.c.get(f"/api/projects/{project_id}")

    def opportunities(self, project_id: str) -> Any:
        return self.c.get(f"/api/projects/{project_id}/opportunities")

    def deliverables(self, project_id: str) -> Any:
        return self.c.get(f"/api/projects/{project_id}/deliverables")

    def analysis(self, project_id: str) -> Any:
        return self.c.get(f"/api/projects/{project_id}/audit-analysis")

    def job_status(self, job_id: str) -> Any:
        return self.c.get(f"/api/agent/jobs/{job_id}")

    # Writes (guarded)

    def create(self, name: str, description: str | None = None, *, confirm: bool = False) -> Any:
        body = {"name": name}
        if description:
            body["description"] = description
        return _guarded_write(self.c, "createProject", "POST", "/api/projects", body, confirm)

    def patch(self, project_id: str, fields: dict, *, confirm: bool = False) -> Any:
        return _guarded_write(self.c, "patchProject", "PATCH",
                              f"/api/projects/{project_id}", fields, confirm, credit_cost=0)

    def trigger_analysis(self, project_id: str, *, confirm: bool = False) -> Any:
        return _guarded_write(self.c, "triggerAuditAnalysis", "POST",
                              f"/api/projects/{project_id}/audit-analysis", None, confirm,
                              timeout=360.0)


class LeadsAPI(_Group):
    def list(self, **params: Any) -> Any:
        return self.c.get("/api/lead-generation/leads", params=params or None)

    def get(self, lead_id: str) -> Any:
        return self.c.get(f"/api/lead-generation/leads/{lead_id}")

    def convert(self, lead_id: str, *, confirm: bool = False) -> Any:
        return _guarded_write(self.c, "convertLead", "POST",
                              f"/api/lead-generation/leads/{lead_id}/convert", None, confirm)


class NucleusAPI(_Group):
    def memories(self, type: str | None = None, project_id: str | None = None) -> Any:
        params = {}
        if type:
            params["type"] = type
        if project_id:
            params["projectId"] = project_id
        return self.c.get("/api/nucleus/memories", params=params or None)

    def captures(self, channel: str | None = None, status: str | None = None,
                 project_id: str | None = None) -> Any:
        params = {}
        if channel:
            params["channel"] = channel
        if status:
            params["status"] = status
        if project_id:
            params["projectId"] = project_id
        return self.c.get("/api/nucleus/captures", params=params or None)

    def capture(self, capture_id: str) -> Any:
        return self.c.get(f"/api/nucleus/captures/{capture_id}")

    def contacts(self, search: str | None = None) -> Any:
        return self.c.get("/api/nucleus/contacts",
                          params={"search": search} if search else None)

    def insights(self, type: str | None = None, unread_only: bool = False,
                 limit: int = 25) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if type:
            params["type"] = type
        if unread_only:
            params["unreadOnly"] = "true"
        return self.c.get("/api/nucleus/insights", params=params)

    def suggestions(self, project_id: str | None = None) -> Any:
        return self.c.get("/api/nucleus/suggestions",
                          params={"projectId": project_id} if project_id else None)

    # Writes (guarded). Live Nucleus mutations require explicit approval.

    def create_memory(self, subject: str, content: str, memory_type: str = "client",
                      project_id: str | None = None, *, confirm: bool = False) -> Any:
        body: dict[str, Any] = {"subject": subject, "content": content,
                                "memoryType": memory_type}
        if project_id:
            body["projectId"] = project_id
        return _guarded_write(self.c, "createMemory", "POST", "/api/nucleus/memories",
                              body, confirm, credit_cost=0)

    def create_capture_note(self, content: str, project_id: str | None = None,
                            *, confirm: bool = False) -> Any:
        body: dict[str, Any] = {"content": content}
        if project_id:
            body["projectId"] = project_id
        return _guarded_write(self.c, "createCaptureNote", "POST",
                              "/api/nucleus/capture/note", body, confirm, credit_cost=0)

    def delete_memory(self, memory_id: str, *, confirm: bool = False) -> Any:
        return _guarded_write(self.c, "deleteMemory", "DELETE",
                              f"/api/nucleus/memories/{memory_id}", None, confirm,
                              credit_cost=0)


def _guarded_write(read_client: AudityClient, operation: str, method: str, path: str,
                   body: dict | None, confirm: bool, credit_cost: Any = None,
                   timeout: float | None = None) -> Any:
    """The write guard. Brief Phase 3: dry run by default, credit check first.

    confirm=False: return a DryRun describing the exact request. No call.
    confirm=True: check credits, refuse if a known cost exceeds the balance,
    then execute on the gated write token (AUDITY_WRITE_TOKEN).
    """
    cost = CREDIT_COSTS.get(operation, credit_cost)
    remaining: int | None = None
    try:
        remaining = int(read_client.get("/api/user/credits").get("remaining"))
    except Exception:
        pass

    if not confirm:
        return DryRun(operation=operation, method=method, path=path, body=body,
                      credit_cost=cost, credits_remaining=remaining)

    if isinstance(cost, int) and cost > 0:
        if remaining is None:
            raise AudityError(0, None,
                              f"Refusing {operation}: could not verify the credit balance.",
                              "GET /api/user/credits must succeed before a credit-spending write.")
        if remaining < cost:
            raise AudityError(402, None,
                              f"Refusing {operation}: cost {cost} exceeds remaining {remaining}.",
                              "Top up credits or wait for the reset.")

    wc = AudityClient.write_client()
    try:
        return wc.request(method, path, json=body, timeout=timeout)
    finally:
        wc.close()


class Audity:
    """Facade: one object, four groups. Audity().account.credits() and so on."""

    def __init__(self, token: str | None = None):
        self.client = AudityClient(token)
        self.account = AccountAPI(self.client)
        self.projects = ProjectsAPI(self.client)
        self.leads = LeadsAPI(self.client)
        self.nucleus = NucleusAPI(self.client)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "Audity":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
