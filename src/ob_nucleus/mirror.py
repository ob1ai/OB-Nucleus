"""Read-only local mirror of Audity client work and Nucleus models.

Targets:
1. SQLite at data/nucleus_mirror.sqlite (always; gitignored). Offline dev,
   local knowledge base, read cache.
2. Supabase BlueprintOS (project mjbbpzwyamymboazabmx) via PostgREST upsert,
   when OBN_SUPABASE_URL and OBN_SUPABASE_SERVICE_KEY are set and the
   schemas in supabase/ have been applied.

Populated exclusively from listProjects, listLeads, listMemories,
listCaptures, listContacts, listInsights. Nothing here ever writes back
to Audity or Nucleus. Mirror, do not fork: Audity is the source of truth.

Live API note (2026-06-07): conversionTimestamp on leads is NOT a
conversion marker (44 of 53 leads carry it unconverted). The only
reliable conversion flag is convertedToAuditId.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .api import Audity

DB_PATH = Path("data") / "nucleus_mirror.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  client_name TEXT,
  status TEXT,
  industry TEXT,
  company_size TEXT,
  description TEXT,
  currency TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  business_name TEXT,
  client_name TEXT,
  client_email TEXT,
  ai_readiness_score REAL,
  composite_score REAL,
  status TEXT,
  converted_to_audit_id TEXT,
  conversion_timestamp TEXT,
  source TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  memory_type TEXT,
  subject TEXT,
  content TEXT,
  source_type TEXT,
  confidence REAL,
  user_id TEXT,
  project_id TEXT,
  stakeholder_id TEXT,
  times_retrieved INTEGER,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS captures (
  id TEXT PRIMARY KEY,
  channel TEXT,
  status TEXT,
  content_type TEXT,
  raw_content TEXT,
  processed_content TEXT,
  processing_results TEXT,
  user_id TEXT,
  project_id TEXT,
  captured_at TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
  id TEXT PRIMARY KEY,
  name TEXT,
  email TEXT,
  phone TEXT,
  company TEXT,
  role TEXT,
  notes TEXT,
  relationship_type TEXT,
  last_interaction_at TEXT,
  created_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS insights (
  id TEXT PRIMARY KEY,
  type TEXT,
  title TEXT,
  body TEXT,
  is_read INTEGER,
  is_dismissed INTEGER,
  project_id TEXT,
  created_at TEXT,
  raw TEXT,
  synced_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT,
  finished_at TEXT,
  counts TEXT,
  supabase_pushed INTEGER,
  status TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items(payload: Any, key: str) -> list[dict]:
    """Unwrap list responses defensively. Shapes vary by endpoint (brief 5.3)."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in (key, "data", "items", "results"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def _row(d: dict, *keys: str) -> list:
    return [d.get(k) for k in keys]


def open_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def sync(db_path: Path = DB_PATH, verbose: bool = True) -> dict:
    """Pull the six Audity reads and upsert into SQLite, then Supabase."""
    started = _now()
    with Audity() as a:
        projects = _items(a.projects.list(), "projects")
        leads = _items(a.leads.list(limit=100), "data")
        memories = _items(a.nucleus.memories(), "memories")
        captures = _items(a.nucleus.captures(), "captures")
        contacts = _items(a.nucleus.contacts(), "contacts")
        insights = _items(a.nucleus.insights(limit=100), "insights")

    conn = open_db(db_path)
    synced = _now()
    with conn:
        for p in projects:
            conn.execute(
                "INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                _row(p, "id", "clientName", "status", "industry", "companySize",
                     "description", "currency", "createdAt", "updatedAt")
                + [json.dumps(p), synced],
            )
        for l in leads:
            conn.execute(
                "INSERT OR REPLACE INTO leads VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _row(l, "id", "businessName", "clientName", "clientEmail",
                     "aiReadinessScore", "compositeScore", "status",
                     "convertedToAuditId", "conversionTimestamp", "source",
                     "createdAt", "updatedAt")
                + [json.dumps(l), synced],
            )
        for m in memories:
            conn.execute(
                "INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _row(m, "id", "memoryType", "subject", "content", "sourceType",
                     "confidence", "userId", "projectId", "stakeholderId",
                     "timesRetrieved", "createdAt", "updatedAt")
                + [json.dumps(m), synced],
            )
        for c in captures:
            conn.execute(
                "INSERT OR REPLACE INTO captures VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _row(c, "id", "channel", "status", "contentType", "rawContent",
                     "processedContent")
                + [json.dumps(c.get("processingResults"))]
                + _row(c, "userId", "projectId", "capturedAt", "createdAt", "updatedAt")
                + [json.dumps(c), synced],
            )
        for ct in contacts:
            conn.execute(
                "INSERT OR REPLACE INTO contacts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                _row(ct, "id", "name", "email", "phone", "company", "role", "notes",
                     "relationshipType", "lastInteractionAt", "createdAt")
                + [json.dumps(ct), synced],
            )
        for i in insights:
            conn.execute(
                "INSERT OR REPLACE INTO insights VALUES (?,?,?,?,?,?,?,?,?,?)",
                [i.get("id"), i.get("insightType") or i.get("type"), i.get("title"),
                 i.get("content") or i.get("body")]
                + [1 if i.get("isRead") else 0, 1 if i.get("isDismissed") else 0]
                + _row(i, "projectId", "createdAt")
                + [json.dumps(i), synced],
            )

    counts = {"projects": len(projects), "leads": len(leads),
              "memories": len(memories), "captures": len(captures),
              "contacts": len(contacts), "insights": len(insights)}

    supabase_pushed = 0
    supabase_note = "skipped (OBN_SUPABASE_URL / OBN_SUPABASE_SERVICE_KEY not set)"
    if os.environ.get("OBN_SUPABASE_URL") and os.environ.get("OBN_SUPABASE_SERVICE_KEY"):
        try:
            supabase_pushed = _push_supabase(projects, leads, memories, captures,
                                             contacts, insights, synced)
            supabase_note = f"upserted {supabase_pushed} rows"
        except Exception as exc:
            supabase_note = f"failed: {exc}"

    with conn:
        conn.execute(
            "INSERT INTO sync_runs (started_at, finished_at, counts, supabase_pushed, status) "
            "VALUES (?,?,?,?,?)",
            [started, _now(), json.dumps(counts), supabase_pushed, "ok"],
        )
    conn.close()

    result = {"counts": counts, "sqlite": str(db_path), "supabase": supabase_note}
    if verbose:
        print(json.dumps(result, indent=2))
    return result


def _sb_rows_projects(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": p.get("id"), "client_name": p.get("clientName"),
        "status": p.get("status"), "industry": p.get("industry"),
        "company_size": p.get("companySize"), "description": p.get("description"),
        "currency": p.get("currency"), "created_at": p.get("createdAt"),
        "updated_at": p.get("updatedAt"), "raw": p, "synced_at": synced,
    } for p in items]


def _sb_rows_leads(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": l.get("id"), "business_name": l.get("businessName"),
        "client_name": l.get("clientName"), "client_email": l.get("clientEmail"),
        "ai_readiness_score": l.get("aiReadinessScore"),
        "composite_score": l.get("compositeScore"), "status": l.get("status"),
        "converted_to_audit_id": l.get("convertedToAuditId"),
        "conversion_timestamp": l.get("conversionTimestamp"),
        "source": l.get("source"), "created_at": l.get("createdAt"),
        "updated_at": l.get("updatedAt"), "raw": l, "synced_at": synced,
    } for l in items]


def _sb_rows_memories(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": m.get("id"), "memory_type": m.get("memoryType"),
        "subject": m.get("subject"), "content": m.get("content"),
        "source_type": m.get("sourceType"), "confidence": m.get("confidence"),
        "user_id": m.get("userId"), "project_id": m.get("projectId"),
        "stakeholder_id": m.get("stakeholderId"),
        "times_retrieved": m.get("timesRetrieved"),
        "created_at": m.get("createdAt"), "updated_at": m.get("updatedAt"),
        "raw": m, "synced_at": synced,
    } for m in items]


def _sb_rows_captures(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": c.get("id"), "channel": c.get("channel"), "status": c.get("status"),
        "content_type": c.get("contentType"), "raw_content": c.get("rawContent"),
        "processed_content": c.get("processedContent"),
        "processing_results": c.get("processingResults"),
        "user_id": c.get("userId"), "project_id": c.get("projectId"),
        "captured_at": c.get("capturedAt"), "created_at": c.get("createdAt"),
        "updated_at": c.get("updatedAt"), "raw": c, "synced_at": synced,
    } for c in items]


def _sb_rows_contacts(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": ct.get("id"), "name": ct.get("name"), "email": ct.get("email"),
        "phone": ct.get("phone"), "company": ct.get("company"), "role": ct.get("role"),
        "notes": ct.get("notes"), "relationship_type": ct.get("relationshipType"),
        "last_interaction_at": ct.get("lastInteractionAt"),
        "created_at": ct.get("createdAt"), "raw": ct, "synced_at": synced,
    } for ct in items]


def _sb_rows_insights(items: list[dict], synced: str) -> list[dict]:
    return [{
        "id": i.get("id"), "type": i.get("insightType") or i.get("type"),
        "title": i.get("title"),
        "body": i.get("content") or i.get("body"), "is_read": bool(i.get("isRead")),
        "is_dismissed": bool(i.get("isDismissed")), "project_id": i.get("projectId"),
        "created_at": i.get("createdAt"), "raw": i, "synced_at": synced,
    } for i in items]


def _push_supabase(projects, leads, memories, captures, contacts, insights,
                   synced: str) -> int:
    """Upsert mirror rows into BlueprintOS via PostgREST. Our database; not an Audity write."""
    url = os.environ["OBN_SUPABASE_URL"].rstrip("/")
    key = os.environ["OBN_SUPABASE_SERVICE_KEY"]
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    tables = {
        "audity_projects": _sb_rows_projects(projects, synced),
        "audity_leads": _sb_rows_leads(leads, synced),
        "nucleus_memories": _sb_rows_memories(memories, synced),
        "nucleus_captures": _sb_rows_captures(captures, synced),
        "nucleus_contacts": _sb_rows_contacts(contacts, synced),
        "nucleus_insights": _sb_rows_insights(insights, synced),
    }
    pushed = 0
    with httpx.Client(timeout=30) as client:
        for table, rows in tables.items():
            if not rows:
                continue
            for start in range(0, len(rows), 500):
                chunk = rows[start:start + 500]
                resp = client.post(f"{url}/rest/v1/{table}?on_conflict=id",
                                   headers=headers, json=chunk)
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Supabase upsert to {table} failed: HTTP {resp.status_code} "
                        f"{resp.text[:200]}. Have the supabase/ schemas been applied?")
                pushed += len(chunk)
                time.sleep(0.2)
    return pushed


def status(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        return {"mirror": "not built yet; run: ob-nucleus mirror sync"}
    conn = open_db(db_path)
    out: dict[str, Any] = {}
    for table in ("projects", "leads", "memories", "captures", "contacts", "insights"):
        out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    last = conn.execute(
        "SELECT finished_at, counts, supabase_pushed, status FROM sync_runs "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        out["last_sync"] = {"finished_at": last[0], "counts": json.loads(last[1]),
                            "supabase_pushed": last[2], "status": last[3]}
    conn.close()
    return out
