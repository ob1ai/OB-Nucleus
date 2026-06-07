# Phase 1 Smoke Test: Audity Connection
Run date: 2026-06-07 (OB1AIRIG, PowerShell, token redacted)
Method: direct REST reads against https://app.auditynow.com with Authorization: Bearer aky_<REDACTED>
MCP server: audity registered at user scope, https://docs.auditynow.com/mcp, status Connected (claude mcp get audity)

| # | Check (brief 4.5) | Endpoint | Result |
|---|---|---|---|
| 1 | Identity | GET /api/user/current | OK. userId user_31Z9OMS2dN1L69RyeJrhB9dsrSI, authMethod pat, patScopes [read] |
| 2 | Tier | GET /api/user/tier | OK. tier agency |
| 3 | Credits | GET /api/user/credits | OK. remaining 50000 of 50000, used 0, projectCreationCost 1000, projectsRemaining 50, canCreateProject true, nextReset 2026-06-19, billingProvider stripe |
| 4 | Projects | GET /api/projects | OK. List returned (see phase1_smoke_raw.json) |
| 5 | Unread insights | GET /api/nucleus/insights?unreadOnly=true | OK. Nucleus is ENABLED for this account |

Verdict: PASS. All five reads succeed. Nucleus enabled.

Discrepancies (brief vs live API, API wins):
1. Brief 4.5 step 4 expects userEmail in the identity response. Live response returns userId and authData only, no userEmail field.

Raw outputs: verification/phase1_smoke_raw.json (token redacted).
