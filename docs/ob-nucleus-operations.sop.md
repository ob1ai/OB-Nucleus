# Operate OB-Nucleus: Audity, Nucleus, and BlueprintOS for the OB.1 Team

Version 1.0.0 (2026-06-07, Chief). Audience: Chloe (with Claudia), Andrew, Evan, and any OB.1 org Claude user. Technical depth optional; every operation here works by asking your Claude agent in plain language.

## Overview

OB-Nucleus makes Audity (AI readiness audits) and Nucleus (client memory) agent-accessible, mirrored into BlueprintOS (our Supabase database). Use this SOP to read client and pipeline intelligence, write memory correctly, and request gated actions. Reads are always free. Writes are guarded and some cost real credits.

## Parameters

- **Repo**: github.com/ob1ai/OB-Nucleus (main branch)
- **Your token**: personal Audity PAT from app.auditynow.com, Settings, API Tokens. Andrew's is read-only by design.
- **BlueprintOS**: Supabase project mjbbpzwyamymboazabmx (active client work only)
- **Daily digest**: read_sweep_<date>.md in the Drive folder Audity_Integration/OB-Nucleus, generated 07:00 daily

## Prerequisites

### Required Setup (one time, 5 minutes; ask your Claude agent to do it for you)

1. You MUST have your own Audity PAT. You MUST NOT share tokens between people or agents (one PAT per surface, per TOKEN_REGISTRY.md).
2. Technical path (Claude Code / Desktop): follow Setup A or B in docs/AUDITY_CONNECTOR_QUALIFICATION.md. This gives your agent 13 audity_* and nucleus_* tools.
3. Non-technical path: no setup. Ask in the Claude org workspace; Chief or your personal agent (Claudia, Buddy) already has access and will run reads for you.

### Required Knowledge

- Reads are free and unlimited within rate limits. Creating a project or converting a lead costs 1,000 credits each and MUST be approved by Chris.
- A lead is converted only if convertedToAuditId is set. You MUST NOT trust conversionTimestamp as a conversion marker.

## Steps

1. Check the daily picture (any team member)
   - Open the latest read_sweep file in the Drive folder, or ask: "What is in today's Audity sweep?"
   - **Validation**: digest dated today; credits, lead triage, and unread insights present.

2. Query client work (any team member)
   - Ask your agent things like: "List active engagements and their stage", "Pull the deliverables for Berman & Killeen", "Which leads scored above 85 and are unconverted?"
   - Agents answer from live Audity or BlueprintOS. Active client work means status past setup, never sandbox or archived rigs.
   - **Validation**: answers cite project or lead IDs.

3. Add knowledge to Nucleus (memory writing, the OB.1 conventions)
   - Meeting transcripts and call notes MUST enter as captures, never pasted as memories. Say: "Capture this note to Nucleus for project X" and confirm when your agent shows the dry run.
   - Durable facts SHOULD become explicit memories after extraction: one fact per memory; subject MUST lead with the client name exactly as in Notion Companies (example: "Berman Killeen: HIPAA scoping status"); client memories MUST carry the projectId; patterns and preferences MUST NOT.
   - You MUST NOT put anything in memory that should not resurface in an unrelated future session. No em dashes anywhere.
   - **Validation**: agent shows the created capture or memory ID.

4. Request a gated action (costs credits or sends outreach)
   - Say what you want: "Convert the USI lead" or "Run analysis on Fairlawn".
   - The agent MUST show you a dry run first: the exact request, the credit cost, and the live balance. Nothing fires without an explicit confirm, and credit-spending actions REQUIRE Chris's approval.
   - **Validation**: you saw cost and balance before anything executed; the action lands in STATUS.md or the conversion queue.

5. Escalate anomalies
   - If the brief, this SOP, or an agent's claim disagrees with a live API response, the API wins. Flag it to Chris, Chloe, or Claudia and it gets logged in STATUS.md.

## Success Criteria

- [ ] You can pull today's sweep and name the top 3 unconverted leads by readiness
- [ ] You can list active engagements with stages without touching the Audity web app
- [ ] A note you captured shows status processed and extracted items within 2 minutes
- [ ] Any write you requested showed a dry run with cost before executing
- [ ] Zero tokens shared, zero secrets in chat or Drive

## Error Handling

### Error: 401 PAT_MALFORMED
**Symptoms**: every call fails immediately. **Cause**: doubled "Bearer" prefix or mangled token. **Resolution**: re-set the env var with the raw aky_ token; regenerate from the dashboard if it persists.

### Error: 403 PAT_SCOPE_INSUFFICIENT on a write
**Symptoms**: reads work, writes refuse. **Cause**: your token is read-only (correct for most people). **Resolution**: route the write request through Chief or ask Chris whether your surface warrants a write token.

### Error: 402 insufficient credits
**Symptoms**: credit-spending write refused. **Cause**: balance below cost. **Resolution**: nothing was spent; raise with Chris; balance resets per billing period (next reset shows in the sweep).

### Error: agent says a table or row is missing in BlueprintOS
**Symptoms**: Supabase query fails or returns empty. **Cause**: schema delta not yet applied or sync scope excludes the row (setup, archived, sandbox). **Resolution**: check STATUS.md for pending schema files; remember BlueprintOS intentionally carries active clients only; the full universe lives in the local SQLite mirror.

## Related SOPs

- **docs/AUDITY_CONNECTOR_QUALIFICATION.md**: connect your own Claude Code or Desktop to the tools
- **config/nucleus_conventions.md**: the full memory writing rules this SOP summarizes
- **docs/PRD_OB1_REVENUE_LOOP.md**: where this system is heading (Attio and Pipeline integration)
- **knowledge/QUICKREF.md**: endpoint, error, and rate limit lookup for technical users
