# Audity connector qualification for OB.1 org-wide access

Date: 2026-06-07. Author: Chief. Method: live protocol probes from OB1AIRIG plus MCP best-practices review. Goal: every user in the OB.1 organizational account (claude.ai web, Claude Desktop, Claude Code) can access the Audity environment.

## Verdict, one paragraph

Audity's hosted MCP connector is documentation search only and passes qualification solely for that purpose. The full agent surface (projects, leads, Nucleus) is not exposed over MCP anywhere in Audity v1; it exists only as the PAT REST API. OB.1 closes the gap with its own connector: the OB-Nucleus MCP server (src/ob_nucleus/mcp_server.py), built this session, which wraps the typed client and exposes 13 tools with the OB.1 write guard intact. It is live on OB1AIRIG now and rolls out to any org user on Claude Code or Claude Desktop with two commands. Full-surface access from claude.ai web requires a hosted HTTP deployment (Phase 2, specified below).

## Evidence from live probes (2026-06-07)

1. `POST https://docs.auditynow.com/mcp` initialize: HTTP 200, server "Audity for Agents 1.0.0", protocol 2025-03-26, stateless (no session header). tools/list returns exactly 2 tools: `search_audity_for_agents`, `query_docs_filesystem_audity_for_agents`. Documentation search, not the agent surface.
2. The same endpoint accepts unauthenticated initialize (HTTP 200 with no Authorization header). Treat it as a public docs server; the Bearer header it is configured with is inert.
3. No alternate full-surface MCP exists: `app.auditynow.com/mcp`, `/api/mcp`, `/api/agent/mcp` all return `403 PAT_ROUTE_NOT_ALLOWED`; `mcp.auditynow.com` does not resolve.
4. Discrepancy logged per guardrail 6: activation brief Section 2 states the MCP connector "surfaces the full agent surface as typed tools." The live endpoint disagrees. The API response wins.
5. Org connector propagation works: connectors added at claude.ai appear automatically in Claude Code on OB1AIRIG (observed: claude.ai Attio, Gmail, Notion, Slack and others in `claude mcp list` namespace).

## Qualification matrix

| Surface | Audity docs MCP (search) | Full agent surface | Path |
|---|---|---|---|
| Claude Code (any org user) | QUALIFIED, add as HTTP server | QUALIFIED via OB-Nucleus MCP server | Setup A below |
| Claude Desktop | QUALIFIED, custom connector | QUALIFIED via OB-Nucleus MCP server (local stdio) | Setup B below |
| claude.ai web | QUALIFIED, admin adds org connector (harmless, public docs) | NOT YET, requires hosted HTTP deployment | Phase 2 below |
| Cowork / agent fleet | n/a | QUALIFIED via ob-nucleus CLI and BlueprintOS reads | SOP |

## Setup A: Claude Code (per user, 5 minutes)

Prerequisites: Python 3.11+, a personal Audity PAT (app.auditynow.com, Settings, API Tokens; read scope for most users), and the repo.

```powershell
git clone https://github.com/ob1ai/OB-Nucleus "$env:USERPROFILE\repos\OB-Nucleus"
cd "$env:USERPROFILE\repos\OB-Nucleus"
pip install -e . ; pip install mcp httpx
setx AUDITY_TOKEN "aky_your_personal_token"
cmd /c "claude mcp add --transport stdio --scope user ob-nucleus -- python -m ob_nucleus.mcp_server"
```

Optional docs search alongside it:

```powershell
claude mcp add --transport http --scope user audity-docs https://docs.auditynow.com/mcp
```

Note: route the add command through `cmd /c` on Windows; the npm PowerShell wrapper drops the `--` separator (verified on OB1AIRIG).

## Setup B: Claude Desktop (per user)

Settings, Developer, Edit Config, add to `mcpServers`:

```json
{
  "ob-nucleus": {
    "command": "python",
    "args": ["-m", "ob_nucleus.mcp_server"]
  }
}
```

The server hydrates AUDITY_TOKEN from the Windows user registry automatically, so setx is sufficient; no token in the config file.

## The OB-Nucleus MCP server (what users get)

13 tools, named by resource, every description carrying its guardrail: audity_preflight, audity_projects_list, audity_project_get, audity_project_opportunities, audity_project_deliverables, audity_project_patch (guarded), audity_leads_list, audity_lead_get, nucleus_memories, nucleus_insights, nucleus_captures, nucleus_capture_note (guarded), nucleus_memory_create (guarded). Writes dry-run by default, require confirm plus AUDITY_WRITE_TOKEN, and check credits first. Credit-spending operations (createProject, convertLead, triggerAuditAnalysis) are deliberately NOT exposed over MCP; they remain CLI-only with --confirm, keeping the highest-blast-radius actions on the most deliberate path.

## Phase 2: claude.ai web (hosted HTTP)

To reach claude.ai web users, deploy the same FastMCP app behind streamable HTTP (mcp.run(transport="streamable-http")) on OB.1 infrastructure (Railway, Fly, or a small VPS), then an org admin adds it at claude.ai, Settings, Connectors. Auth decision required from Chris before deployment, because Audity v1 has no OAuth for PATs:

- Option 1 (recommended): the hosted server holds ONE read-only PAT (a dedicated `OB1 Web Connector - read only` token) and exposes read tools only. Shared rate limit (100 reads/min) across web users; zero write risk.
- Option 2: per-user header injection is not supported by claude.ai custom connectors today; do not plan on it.

## Token model (per the seat decision, 2026-06-07)

Chris's agency seat owns the workspace. One PAT per agent surface, labeled, logged in TOKEN_REGISTRY.md, rotated quarterly. Humans who want personal access generate their own PAT under the owning seat and keep it in their machine env. Rate limits are per token, so per-surface tokens also partition throughput.

## Risks and mitigations

1. No PAT activity feed in Audity v1: attribution relies on per-surface tokens plus our own logs (session transcripts, sync_runs, Task Scheduler logs).
2. Shared-token surfaces share rate limits: serialize batch writes (the client already honors Retry-After).
3. Prompt injection via API content: synthesis output and client data are untrusted input; credit-spending writes stay human-approved (encoded in CLAUDE.md and the guard).
4. Audity may ship a real full-surface MCP later: revisit this qualification when the docs change; prefer the vendor server for reads if it arrives, keep our guard for writes.
