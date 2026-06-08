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

Integrity machinery (lane 1, 2026-06-07):
- sync_runs audit rows land in SQLite and in the Supabase sync_runs table.
- Stale Supabase project rows are purged when Audity archives a project
  mid-cycle (statuses flip to archived between reads; observed live 6/7).
  Hard delete in Supabase is safe descoping, not data loss: SQLite keeps
  the full universe and the raw JSON history.
- drift_check() compares live API vs SQLite vs Supabase per table, with
  freshness and duplicate-name anomaly flags, for the daily digest.
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

# Supabase freshness threshold for drift flags. The sweep runs daily at
# 07:00; 26 hours allows one slow or delayed run before flagging.
STALE_HOURS = 26

# SQLite table -> Supabase table
SB_TABLE_MAP = {
    "projects": "audity_projects",
    "leads": "audity_leads",
    "memories": "nucleus_memories",
    "captures": "nucleus_captures",
    "contacts": "nucleus_contacts",
    "insights": "nucleus_insights",
}


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


EXCLUDED_PROJECT_STATUSES = {"setup", "archived"}


def _test_client_prefixes() -> tuple[str, ...]:
    """Test-rig exclusion list. Default covers the sandbox rigs; extend
    without a code change via OBN_TEST_CLIENT_PREFIXES (comma separated,
    case insensitive). Maintained by lane 1.
    """
    raw = os.environ.get("OBN_TEST_CLIENT_PREFIXES", "sandbox")
    return tuple(p.strip().lower() for p in raw.split(",") if p.strip())


def active_clients(projects: list[dict]) -> list[dict]:
    """OB.1 scope rule (Chris, 2026-06-07): BlueprintOS carries active client
    work only. Active means the engagement is in flight (status past setup)
    and the client is real (no sandbox or test rigs). The local SQLite mirror
    always keeps everything; this filter governs the Supabase push only.
    Override with OBN_SYNC_SCOPE=all for a full push.
    """
    prefixes = _test_client_prefixes()
    out = []
    for p in projects:
        status = (p.get("status") or "").lower()
        name = (p.get("clientName") or "").lower()
        if status in EXCLUDED_PROJECT_STATUSES:
            continue
        if name.startswith(prefixes):
            continue
        out.append(p)
    return out


# Trailing legal-form suffixes dropped during name normalization. Verified
# against the live Cleveland Candy pair: 'Cleveland Candy Co.' (interviews)
# vs 'Cleveland Candy Company' (setup) normalize to the same key.
_NAME_SUFFIXES = {"co", "company", "inc", "incorporated", "llc", "ltd",
                  "limited", "corp", "corporation", "gmbh", "plc", "lp", "llp"}


def _normalized_name(value: str | None) -> str:
    """Collapse case, punctuation, whitespace, and trailing legal suffixes
    for duplicate detection (Cleveland Candy case: same client, two
    spellings). Detection only; merging is a human decision, never automated.
    """
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " "
                      for ch in (value or "").lower())
    tokens = cleaned.split()
    while tokens and tokens[-1] in _NAME_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def open_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _sb_env() -> tuple[str, str] | None:
    url = os.environ.get("OBN_SUPABASE_URL")
    key = os.environ.get("OBN_SUPABASE_SERVICE_KEY")
    if url and key:
        return url.rstrip("/"), key
    return None


def _sb_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


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
    purged = 0
    status_label = "ok"
    supabase_note = "skipped (OBN_SUPABASE_URL / OBN_SUPABASE_SERVICE_KEY not set)"
    env = _sb_env()
    if env:
        try:
            scope = os.environ.get("OBN_SYNC_SCOPE", "active").lower()
            sb_projects = projects if scope == "all" else active_clients(projects)
            supabase_pushed = _push_supabase(sb_projects, leads, memories, captures,
                                             contacts, insights, synced)
            purged = _purge_stale_projects(env, sb_projects)
            supabase_note = (f"upserted {supabase_pushed} rows (scope={scope}, "
                             f"projects pushed {len(sb_projects)} of {len(projects)}, "
                             f"stale projects purged {purged})")
        except Exception as exc:
            status_label = "supabase_failed"
            supabase_note = f"failed: {exc}"

    finished = _now()
    with conn:
        conn.execute(
            "INSERT INTO sync_runs (started_at, finished_at, counts, supabase_pushed, status) "
            "VALUES (?,?,?,?,?)",
            [started, finished, json.dumps(counts), supabase_pushed, status_label],
        )
    conn.close()

    sync_run_remote = "skipped (Supabase env not set)"
    if env:
        sync_run_remote = _log_sync_run_remote(env, started, finished, counts,
                                               supabase_pushed, status_label)

    result = {"counts": counts, "sqlite": str(db_path), "supabase": supabase_note,
              "sync_run_remote": sync_run_remote}
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
    url, key = _sb_env()
    headers = _sb_headers(key)
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


def _purge_stale_projects(env: tuple[str, str], current: list[dict]) -> int:
    """Delete Supabase audity_projects rows that fell out of sync scope.

    Audity archives projects mid-cycle (statuses flip to archived between
    reads, observed live 2026-06-07). The push filter excludes them going
    forward; this removes rows pushed before the flip. Hard delete here is
    descoping, not data loss: SQLite keeps the full universe and raw JSON.

    Guard: never purges when the current set is empty, so a transient empty
    API response cannot wipe the table.
    """
    if not current:
        return 0
    ids = ",".join(f'"{p["id"]}"' for p in current if p.get("id"))
    if not ids:
        return 0
    url, key = env
    headers = _sb_headers(key)
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=30) as client:
        resp = client.delete(
            f"{url}/rest/v1/audity_projects?id=not.in.({ids})&select=id",
            headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase stale-project purge failed: HTTP {resp.status_code} "
            f"{resp.text[:200]}")
    try:
        return len(resp.json())
    except Exception:
        return 0


def _log_sync_run_remote(env: tuple[str, str], started: str, finished: str,
                         counts: dict, supabase_pushed: int,
                         status_label: str) -> str:
    """Append the sync audit row to the Supabase sync_runs table.

    Best effort by design: a remote logging failure must never fail the
    sync itself (SQLite already holds the authoritative audit row).
    Returns a short status string for the sync result payload.
    """
    url, key = env
    row = {"started_at": started, "finished_at": finished, "counts": counts,
           "supabase_pushed": supabase_pushed, "status": status_label}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(f"{url}/rest/v1/sync_runs",
                               headers=_sb_headers(key), json=row)
        if resp.status_code >= 400:
            return f"failed: HTTP {resp.status_code} {resp.text[:200]}"
        return "logged"
    except Exception as exc:
        return f"failed: {exc}"


def _sb_count(client: httpx.Client, url: str, headers: dict, table: str) -> int | None:
    resp = client.get(f"{url}/rest/v1/{table}?select=id&limit=1",
                      headers={**headers, "Prefer": "count=exact"})
    if resp.status_code >= 400:
        return None
    content_range = resp.headers.get("content-range", "")
    try:
        return int(content_range.split("/")[-1])
    except ValueError:
        return None


def _sb_latest(client: httpx.Client, url: str, headers: dict, table: str,
               column: str) -> str | None:
    resp = client.get(
        f"{url}/rest/v1/{table}?select={column}&order={column}.desc.nullslast&limit=1",
        headers=headers)
    if resp.status_code >= 400:
        return None
    try:
        rows = resp.json()
        return rows[0].get(column) if rows else None
    except Exception:
        return None


def _hours_since(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - parsed).total_seconds() / 3600
    except ValueError:
        return None


def drift_check(db_path: Path = DB_PATH, verbose: bool = False) -> dict:
    """Three-way integrity check: live Audity reads vs SQLite vs Supabase.

    Reads only; zero credit risk. Per table: live count, SQLite count,
    Supabase count against the scope-adjusted expectation, and Supabase
    freshness (newest synced_at). Anomaly flags cover count mismatches,
    staleness past STALE_HOURS, missing remote sync_runs rows, and
    duplicate active client names (flagged for human merge, never merged
    automatically).
    """
    with Audity() as a:
        projects = _items(a.projects.list(), "projects")
        leads = _items(a.leads.list(limit=100), "data")
        memories = _items(a.nucleus.memories(), "memories")
        captures = _items(a.nucleus.captures(), "captures")
        contacts = _items(a.nucleus.contacts(), "contacts")
        insights = _items(a.nucleus.insights(limit=100), "insights")

    live = {"projects": len(projects), "leads": len(leads),
            "memories": len(memories), "captures": len(captures),
            "contacts": len(contacts), "insights": len(insights)}

    scope = os.environ.get("OBN_SYNC_SCOPE", "active").lower()
    active = projects if scope == "all" else active_clients(projects)
    expected_sb = dict(live)
    expected_sb["projects"] = len(active)

    sqlite_counts: dict[str, int] = {}
    if db_path.exists():
        conn = open_db(db_path)
        for t in live:
            sqlite_counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        conn.close()

    flags: list[str] = []
    sb_counts: dict[str, int | None] = {}
    sb_fresh: dict[str, str | None] = {}
    sync_runs_remote: dict | None = None
    env = _sb_env()
    if env:
        url, key = env
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        with httpx.Client(timeout=30) as client:
            for t, sb_t in SB_TABLE_MAP.items():
                sb_counts[t] = _sb_count(client, url, headers, sb_t)
                sb_fresh[t] = _sb_latest(client, url, headers, sb_t, "synced_at")
            sync_runs_remote = {
                "count": _sb_count(client, url, headers, "sync_runs"),
                "latest_finished_at": _sb_latest(client, url, headers,
                                                 "sync_runs", "finished_at"),
            }
    else:
        flags.append("supabase: env not set, remote checks skipped")

    tables: dict[str, dict] = {}
    for t in live:
        tables[t] = {"live": live[t], "sqlite": sqlite_counts.get(t),
                     "supabase": sb_counts.get(t),
                     "supabase_expected": expected_sb[t],
                     "supabase_max_synced_at": sb_fresh.get(t)}
        if not sqlite_counts:
            pass
        elif sqlite_counts.get(t) != live[t]:
            flags.append(f"{t}: SQLite {sqlite_counts.get(t)} != live {live[t]} "
                         f"(run mirror sync)")
        if env:
            if sb_counts.get(t) is None:
                flags.append(f"{t}: Supabase count unavailable")
            elif sb_counts[t] != expected_sb[t]:
                flags.append(f"{t}: Supabase {sb_counts[t]} != expected "
                             f"{expected_sb[t]} (scope={scope})")
            age = _hours_since(sb_fresh.get(t))
            if age is not None and age > STALE_HOURS:
                flags.append(f"{t}: Supabase freshest row is {age:.0f}h old "
                             f"(threshold {STALE_HOURS}h)")
    if not sqlite_counts:
        flags.append("sqlite: mirror not built yet (run mirror sync)")

    if env and sync_runs_remote is not None:
        if not sync_runs_remote["count"]:
            flags.append("sync_runs: no remote audit rows in Supabase")
        else:
            age = _hours_since(sync_runs_remote["latest_finished_at"])
            if age is not None and age > STALE_HOURS:
                flags.append(f"sync_runs: latest remote run is {age:.0f}h old "
                             f"(threshold {STALE_HOURS}h)")

    names: dict[str, list[str]] = {}
    for p in active:
        key_name = _normalized_name(p.get("clientName"))
        if key_name:
            names.setdefault(key_name, []).append(str(p.get("id")))
    for key_name, ids in sorted(names.items()):
        if len(ids) > 1:
            flags.append(f"projects: duplicate active client name '{key_name}' "
                         f"({len(ids)} rows: {', '.join(ids)}); human merge "
                         f"decision needed, never auto-merge")

    result = {"checked_at": _now(), "scope": scope, "tables": tables,
              "sync_runs_remote": sync_runs_remote,
              "flags": flags or ["none: live API, SQLite, and Supabase agree"]}
    if verbose:
        print(json.dumps(result, indent=2))
    return result


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
