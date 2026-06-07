# HANDOFF Lane 2: org connector rollout

Paste into a fresh OB-Nucleus project chat. You are Chief, lane 2 of 6. Read first: handoffs/00_INDEX_THE_LARGER_PICTURE.md, docs/AUDITY_CONNECTOR_QUALIFICATION.md, repo STATUS.md.

## Mission

Every OB.1 seat (human or agent, on claude.ai, Claude Desktop, or Claude Code) reaches the Audity environment safely, on its own token, with the write guard intact. The qualification found that Audity's hosted MCP is documentation search only; OB.1's own MCP server closes the gap and you own its rollout and hardening.

## What exists and is verified

- src/ob_nucleus/mcp_server.py: 13 guarded tools (audity_*, nucleus_*), FastMCP stdio, registry-hydrating auth, registered user-scope on OB1AIRIG and Connected. Credit-spending operations are deliberately CLI-only.
- docs/AUDITY_CONNECTOR_QUALIFICATION.md: full verdict, per-surface setup (Setup A: Claude Code; Setup B: Desktop), Phase 2 hosted-HTTP spec with the auth decision Chris must make, risk register.
- Windows gotcha: route claude mcp add through cmd /c because the npm PowerShell wrapper drops the -- separator.
- Org connectors added at claude.ai propagate to Claude Code automatically (observed on OB1AIRIG).

## Scope (yours)

1. Onboard the first two non-Chief seats (Chloe/Claudia and Buddy on Chris's other machines) per Setup A or B, each with their own PAT, each logged in TOKEN_REGISTRY.md (Drive folder).
2. Harden the server: pagination on list tools, output size discipline (large deliverables payloads), tool annotations, version pinning, a smoke-test script (scripts/mcp_smoke.py) that initializes stdio and calls audity_preflight.
3. Drive the Phase 2 decision with Chris: hosted streamable-HTTP deployment for claude.ai web, Option 1 (dedicated read-only PAT, read tools only) per the qualification doc. Deploy only after his sign-off.
4. Watch the vendor: re-probe docs.auditynow.com/mcp monthly; if Audity ships a real full-surface MCP, re-qualify and prefer it for reads.

## Non-goals (other lanes)

Schema changes (lane 1). Attio/Pipeline integration (lane 3). SOP content (lane 4). New Audity API features beyond the existing client.

## First three actions

1. Verify ob-nucleus MCP still Connected (claude mcp get ob-nucleus) and run a tool call end to end.
2. Write scripts/mcp_smoke.py and commit on chief/lane-02-connector.
3. Schedule the Chloe onboarding session; prepare her PAT issuance checklist (she creates it in her own browser session; you never see the value).

## Definition of done

Two or more non-Chief seats running the tools on their own PATs; smoke script in repo; Phase 2 decision recorded in STATUS.md (deployed, deferred, or declined); registry current.

## Needs humans

Chris: Phase 2 auth decision; PAT issuance approvals. Chloe: 20 minutes for onboarding. No credits involved.
