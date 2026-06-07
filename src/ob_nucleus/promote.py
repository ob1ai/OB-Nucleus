"""Capture-to-memory promote helper (brief 5.5, 5.9). GATED, never auto-run.

The OB.1 promote path: transcript goes in as a capture, the extraction job
distills it, and the distilled facts become explicit memories (and a row in
the Notion Decisions Log, handled outside this module).

Default behavior is a dry run that prints the memory payloads it would
create. Executing requires confirm=True, which routes through the write
guard: credit check, AUDITY_WRITE_TOKEN, and explicit approval from Chris.
This module was written in the initial build session and deliberately not
executed there.
"""

from __future__ import annotations

import time
from typing import Any

from .api import Audity, DryRun
from .client import AudityError

WRITE_DELAY_SECONDS = 3.5  # stay under the 20/min write ceiling (brief 8)


def _draft_subject(text: str, client_name: str | None) -> str:
    """Subjects are addressable (conventions): lead with the client name."""
    stub = " ".join(text.split())[:70].rstrip(".,;: ")
    return f"{client_name}: {stub}" if client_name else stub


def draft_promotions(capture_payload: dict, client_name: str | None = None) -> list[dict]:
    """Build memory payloads from a processed capture's extracted items.

    One fact per memory (conventions). Decisions and key insights are
    promoted; action items belong in the task system, not Nucleus.
    """
    capture = capture_payload.get("capture", capture_payload)
    items = capture_payload.get("items") or []
    project_id = capture.get("projectId")

    drafts: list[dict] = []
    for item in items:
        kind = (item.get("type") or item.get("itemType") or "").lower()
        text = item.get("content") or item.get("text") or ""
        if not text:
            continue
        if "action" in kind:
            continue  # task system territory, not memory
        drafts.append({
            "subject": _draft_subject(text, client_name),
            "content": text,
            "memoryType": "client" if project_id else "pattern",
            "projectId": project_id,
        })
    return drafts


def promote_capture(capture_id: str, client_name: str | None = None,
                    *, confirm: bool = False) -> dict:
    """Read one capture and promote its extracted items to explicit memories.

    confirm=False (default): returns the plan, makes no write.
    confirm=True: requires AUDITY_WRITE_TOKEN and explicit approval.
    """
    with Audity() as a:
        payload = a.nucleus.capture(capture_id)
        capture = payload.get("capture", payload)
        status = capture.get("status")
        if status != "processed":
            raise AudityError(0, None,
                              f"Capture {capture_id} is '{status}', not 'processed'.",
                              "Wait for extraction to finish, or reprocess a failed capture.")

        drafts = draft_promotions(payload, client_name)
        if not drafts:
            return {"capture_id": capture_id, "promoted": 0,
                    "note": "No promotable items (decisions / key insights) found."}

        if not confirm:
            return {
                "dry_run": True,
                "capture_id": capture_id,
                "would_create_memories": drafts,
                "note": ("DRY RUN: no memory was written. Re-run with confirm=True "
                         "(CLI: --confirm) only with explicit approval from Chris."),
            }

        created: list[Any] = []
        for draft in drafts:
            res = a.nucleus.create_memory(
                draft["subject"], draft["content"], draft["memoryType"],
                draft.get("projectId"), confirm=True)
            created.append(res if not isinstance(res, DryRun) else res.to_dict())
            time.sleep(WRITE_DELAY_SECONDS)
        return {"capture_id": capture_id, "promoted": len(created), "results": created}
