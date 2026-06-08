"""Daily read-only digest (brief Section 10 step 4).

Credits, lead triage, unread insights, BlueprintOS drift check.
Reads only; zero credit risk. Writes a dated markdown digest to
verification/ and returns it.

Note: scripts/daily_sweep.ps1 runs mirror sync before this sweep so the
drift section reflects the post-sync state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .api import Audity

OUT_DIR = Path("verification")


def _leads_list(payload) -> list[dict]:
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("leads") or []
    return payload or []


def _insights_list(payload) -> list[dict]:
    if isinstance(payload, dict):
        return payload.get("insights") or payload.get("data") or []
    return payload or []


def _short_ts(value) -> str:
    return str(value)[:19] if value else "n/a"


def _drift_lines() -> list[str]:
    """BlueprintOS drift section: live API vs SQLite vs Supabase.

    Never breaks the sweep; failure renders as a single explanatory line.
    """
    lines = ["## BlueprintOS drift check"]
    try:
        from .mirror import drift_check
        drift = drift_check()
        for table, row in drift["tables"].items():
            lines.append(
                f"- {table}: live {row['live']}, sqlite {row['sqlite']}, "
                f"supabase {row['supabase']} (expected {row['supabase_expected']}), "
                f"freshest {_short_ts(row['supabase_max_synced_at'])}")
        remote = drift.get("sync_runs_remote") or {}
        lines.append(f"- sync_runs (remote): {remote.get('count', 'n/a')} rows, "
                     f"latest {_short_ts(remote.get('latest_finished_at'))}")
        lines += ["", "### Drift flags"]
        for flag in drift["flags"]:
            lines.append(f"- {flag}")
    except Exception as exc:
        lines.append(f"- drift check unavailable: {exc}")
    return lines


def run_sweep(out_dir: Path = OUT_DIR) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with Audity() as a:
        credits = a.account.credits()
        leads_raw = a.leads.list(status="active", sortBy="ai_readiness_score",
                                 sortOrder="desc", limit=50)
        insights_raw = a.nucleus.insights(unread_only=True)

    leads = [l for l in _leads_list(leads_raw)
             if not l.get("convertedToAuditId")
             and (l.get("status") or l.get("surveyStatus") or "") != "converted"]
    insights = _insights_list(insights_raw)

    lines = [
        f"# OB.1 read sweep: {today}",
        "",
        "## Credits",
        f"- Remaining: {credits.get('remaining')} of {credits.get('allocated')} "
        f"(used {credits.get('used')}, {credits.get('usagePercentage')}%)",
        f"- Project creation cost: {credits.get('projectCreationCost')}; "
        f"projects remaining: {credits.get('projectsRemaining')}",
        f"- Next reset: {credits.get('nextReset')} "
        f"({credits.get('daysUntilReset')} days)",
        "",
        f"## Lead triage ({len(leads)} active, unconverted)",
    ]
    if leads:
        for l in leads[:10]:
            lines.append(
                f"- {l.get('businessName') or l.get('clientName') or l.get('id')}: "
                f"readiness {l.get('aiReadinessScore') or l.get('ai_readiness_score') or 'n/a'}, "
                f"status {l.get('status') or 'n/a'}, created {str(l.get('createdAt'))[:10]}")
        if len(leads) > 10:
            lines.append(f"- ... and {len(leads) - 10} more")
    else:
        lines.append("- No active unconverted leads.")

    lines += ["", f"## Unread Nucleus insights ({len(insights)})"]
    if insights:
        for i in insights[:15]:
            lines.append(f"- [{i.get('insightType') or i.get('type')}] {i.get('title')}: "
                         f"{(i.get('content') or i.get('body') or '')[:140]}")
    else:
        lines.append("- Inbox zero. No unread insights.")

    lines += [""] + _drift_lines()

    lines += ["", "Reads only. No credits were spent generating this digest.", ""]
    digest = "\n".join(lines)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"read_sweep_{today}.md"
    out_path.write_text(digest, encoding="utf-8")
    return digest
