# OB-Nucleus handoff index: the larger picture

Date: 2026-06-07. Author: Chief (founding session). Purpose: split one overloaded thread into six clean lanes, each owned by a fresh chat in this project.

## The flywheel every lane serves

```
Audity discovers  ->  Nucleus remembers  ->  BlueprintOS holds the data
      ^                                              |
      |                                              v
Engagements deliver  <-  Attio + Pipeline turn intelligence into revenue
```

Audity is the readiness and discovery engine. Nucleus is the cross-engagement memory. BlueprintOS (Supabase) is OB.1's own queryable data layer, scoped to active client work. Attio and Pipeline convert that intelligence into booked revenue. Engagements feed memory back in, and the loop compounds. GaaS discipline applied to our own operations first: rules before tools.

## Why six chats

The founding session built the foundation and then absorbed six distinct missions. Context drift follows from that pattern, not from any one task. Each lane below gets a self-contained kickoff file. Open a fresh chat, paste or reference the handoff, and the lane runs without this history.

| Lane | File | Mission in one line | Definition of done |
|---|---|---|---|
| 1 | 01_DATA_LAYER.md | BlueprintOS schema and sync integrity | schema_v3 live, sync_runs remote, drift checks in the sweep |
| 2 | 02_CONNECTOR_ROLLOUT.md | Every OB.1 seat reaches Audity safely | 2+ non-Chief seats live on their own PATs, Phase 2 decision recorded |
| 3 | 03_REVENUE_LOOP.md | Execute PRD OB1-INT-2606-001 (Attio + Pipeline) | Scribe default-on, active book visible in Attio, Steward dry-runs approved |
| 4 | 04_TEAM_ENABLEMENT.md | Humans fluent on the SOP | 3 humans pass the SOP success criteria, registry current |
| 5 | 05_STAKEHOLDER_COMMS.md | Team, advisors, stakeholders stay briefed | Deck render-verified and sent, recurring brief cadence live |
| 6 | 06_AUTOMATION_W1.md | Granola to Nucleus pipeline, then the ladder | W1 at canary, 95% of client meetings captured within 24h |

## Ground truth (all lanes inherit this)

- Repo: github.com/ob1ai/OB-Nucleus. Local: C:\Users\admin\repos\OB-Nucleus. main is current; never inside Google Drive.
- Drive folder (team surface): G:\Shared drives\OB.1 Business Docs\05_TECHNICAL_DEVELOPMENT\Audity_Integration\OB-Nucleus
- Env vars on OB1AIRIG (names only, values in user registry): AUDITY_TOKEN (read), AUDITY_WRITE_TOKEN (gated), OBN_SUPABASE_URL, OBN_SUPABASE_SERVICE_KEY, OBN_SYNC_SCOPE. Shells must hydrate: [Environment]::GetEnvironmentVariable('NAME','User').
- BlueprintOS: Supabase project mjbbpzwyamymboazabmx. Tables: nucleus_memories, nucleus_captures, nucleus_contacts, nucleus_insights, audity_projects, audity_leads, sync_runs. Scope: active clients only (status past setup, not archived, no sandbox). SQLite mirror at data/ holds everything.
- Tooling: ob-nucleus CLI (pip install -e .), OB-Nucleus MCP server (13 guarded tools, user scope), audity docs-search MCP. Daily sweep: Task Scheduler "OB1 Audity Daily Sweep" 07:00.
- Verified API truths (API wins over the brief): a lead is converted only if convertedToAuditId is set; insights use insightType and content with no projectId; Audity's hosted MCP is docs-search only; captures auto-create extracted memories.
- Credits: 50,000 of 50,000. createProject and convertLead cost 1,000 each. GlobalTech conversion is HELD (test lead); USI Insurance (92) is the live candidate.
- People: Chris approves credit spends, merges, outbound sends. Chloe owns Attio list creation. Matt owns Pipeline. Andrew is read-only. Claudia and Buddy are personal agents.

## Coordination protocol (anti-drift mechanics)

1. One lane per chat. If work belongs to another lane, write one line in STATUS.md under "Lane updates" and stop. Do not do another lane's work.
2. Session start ritual: read your handoff file, then repo STATUS.md, then repo CLAUDE.md. Nothing else is required context.
3. Session end ritual: append a dated lane update to STATUS.md, commit on branch chief/lane-NN-topic, push. Chris merges to main.
4. Global guardrails in every lane: reads free, writes gated behind --confirm with credit check, write token only with explicit approval, no em dashes anywhere, probe live API shapes before parsing them, API beats documentation, log discrepancies in STATUS.md, no secrets in git or chat.
5. Escalation: anything ambiguous about scope goes to Chris, not to a guess.
