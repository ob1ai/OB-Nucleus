"""OB-Nucleus MCP server: the full Audity agent surface as typed MCP tools.

Why this exists: Audity's hosted MCP (docs.auditynow.com/mcp) is documentation
search only (verified 2026-06-07: two tools, unauthenticated). No PAT-accessible
full-surface MCP exists in v1. This server closes the gap by wrapping the
OB-Nucleus typed client, so any Claude Code or Claude Desktop user with their
own AUDITY_TOKEN gets projects, leads, and Nucleus as first class tools with
the OB.1 write guard intact.

Run (stdio):  python -m ob_nucleus.mcp_server
Register:     claude mcp add --transport stdio --scope user ob-nucleus -- python -m ob_nucleus.mcp_server

Auth: reads AUDITY_TOKEN from the environment; on Windows falls back to the
user registry so Task Scheduler and fresh shells work. Writes additionally
require AUDITY_WRITE_TOKEN and confirm=true, and always check credits first.
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api import Audity, DryRun

mcp = FastMCP("ob-nucleus")


def _hydrate_env() -> None:
    """Windows quirk: setx values are invisible to already-running hosts."""
    if os.name != "nt":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in ("AUDITY_TOKEN", "AUDITY_WRITE_TOKEN",
                         "OBN_SUPABASE_URL", "OBN_SUPABASE_SERVICE_KEY"):
                if not os.environ.get(name):
                    try:
                        os.environ[name] = winreg.QueryValueEx(key, name)[0]
                    except OSError:
                        pass
    except Exception:
        pass


def _out(result: Any) -> str:
    if isinstance(result, DryRun):
        result = result.to_dict()
    return json.dumps(result, indent=2, default=str)


# Account

@mcp.tool()
def audity_preflight() -> str:
    """Identity, tier, and credit balance in one call. Run at session start.
    Always read credits here before proposing any credit-spending write."""
    with Audity() as a:
        return _out(a.account.preflight())


# Projects (active audit / client work)

@mcp.tool()
def audity_projects_list() -> str:
    """List all Audity projects (active audit and client work) with status."""
    with Audity() as a:
        return _out(a.projects.list())


@mcp.tool()
def audity_project_get(project_id: str) -> str:
    """Full detail for one project, including uploaded documents."""
    with Audity() as a:
        return _out(a.projects.get(project_id))


@mcp.tool()
def audity_project_opportunities(project_id: str) -> str:
    """Opportunity list (impact and effort scores) for a project."""
    with Audity() as a:
        return _out(a.projects.opportunities(project_id))


@mcp.tool()
def audity_project_deliverables(project_id: str) -> str:
    """Deliverables dashboard: executive summary, opportunities, risks,
    stakeholder memos. Returns 404 until an analysis has run."""
    with Audity() as a:
        return _out(a.projects.deliverables(project_id))


@mcp.tool()
def audity_project_patch(project_id: str, name: str = "", description: str = "",
                         confirm: bool = False) -> str:
    """Update project name or description. Zero credits but a live write:
    dry run unless confirm=true. Requires AUDITY_WRITE_TOKEN when confirmed."""
    fields = {k: v for k, v in (("name", name), ("description", description)) if v}
    with Audity() as a:
        return _out(a.projects.patch(project_id, fields, confirm=confirm))


# Leads

@mcp.tool()
def audity_leads_list(status: str = "", limit: int = 50) -> str:
    """List leads with AI readiness scores. Conversion truth: a lead is
    converted only if convertedToAuditId is set; conversionTimestamp alone
    is NOT a conversion marker (verified live 2026-06-07)."""
    params: dict[str, Any] = {"limit": limit}
    if status:
        params["status"] = status
    with Audity() as a:
        return _out(a.leads.list(**params))


@mcp.tool()
def audity_lead_get(lead_id: str) -> str:
    """Full detail for one lead, including survey responses and AI analysis."""
    with Audity() as a:
        return _out(a.leads.get(lead_id))


# Nucleus memory layer

@mcp.tool()
def nucleus_memories(memory_type: str = "", project_id: str = "") -> str:
    """List Nucleus memories. Types: client, pattern, preference. Trust model:
    explicit memories are facts, extracted need verification, detected are
    hypotheses weighted by confidence."""
    with Audity() as a:
        return _out(a.nucleus.memories(memory_type or None, project_id or None))


@mcp.tool()
def nucleus_insights(unread_only: bool = True, limit: int = 25) -> str:
    """Proactive Nucleus insights. Live types: overdue_followup,
    pattern_detected, similar_lead, stale_client."""
    with Audity() as a:
        return _out(a.nucleus.insights(None, unread_only, limit))


@mcp.tool()
def nucleus_captures(status: str = "", project_id: str = "") -> str:
    """List Nucleus captures (the intake funnel for transcripts and notes)."""
    with Audity() as a:
        return _out(a.nucleus.captures(None, status or None, project_id or None))


@mcp.tool()
def nucleus_capture_note(content: str, project_id: str = "",
                         confirm: bool = False) -> str:
    """Submit a text note to Nucleus (50k chars max, 30/hour). Extraction runs
    asynchronously and auto-creates extracted memories. Zero credits but a live
    write: dry run unless confirm=true. Follow OB.1 conventions: transcripts
    and notes enter as captures, never pasted directly into memories."""
    with Audity() as a:
        return _out(a.nucleus.create_capture_note(content, project_id or None,
                                                  confirm=confirm))


@mcp.tool()
def nucleus_memory_create(subject: str, content: str, memory_type: str = "client",
                          project_id: str = "", confirm: bool = False) -> str:
    """Create an explicit Nucleus memory. OB.1 conventions: subject leads with
    the client name as it appears in Notion Companies; one fact per memory;
    client memories require project_id; patterns and preferences never carry
    one; no em dashes. Dry run unless confirm=true."""
    with Audity() as a:
        return _out(a.nucleus.create_memory(subject, content, memory_type,
                                            project_id or None, confirm=confirm))


def main() -> None:
    _hydrate_env()
    mcp.run()


if __name__ == "__main__":
    main()
