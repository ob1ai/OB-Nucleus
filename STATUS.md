# STATUS: OB-Nucleus initial build

Date: 2026-06-07. Agent: Chief on OB1AIRIG. Branch: chief/initial-build. Session: reads only, zero credits spent.

## Built

- Connection: Audity MCP server registered at user scope (claude mcp get audity: Connected). Tokens set as user environment variables; read token active, write token gated and unused.
- Scaffold: README.md, CLAUDE.md, .gitignore, .env.example, knowledge/ (activation brief copy + QUICKREF.md distilled from brief Sections 7 and 8).
- Client library: src/ob_nucleus/, Python with httpx (argparse CLI, stdlib, documented in README). Groups: account, projects, leads, nucleus. One auth path, 429 Retry-After backoff, 5xx retries, brief Section 8 error mapping with hints, token redaction in error text.
- Write guard: every write defaults to a dry run printing the exact request, the credit cost, and the live balance. confirm=True checks credits first and requires the gated AUDITY_WRITE_TOKEN. Verified live: createProject without --confirm returned the dry run and made no call.
- CLI: ob-nucleus <group> <command> via pip install -e . (also python -m ob_nucleus.cli, or cli\ob_nucleus_cli.py with no install).
- Nucleus config: config/nucleus_conventions.md (brief 5.9), config/taxonomy.md (brief 5, live vs reserved insight types), config/nucleus_schema.sql.
- Mirror: data/nucleus_mirror.sqlite populated read-only from listMemories, listCaptures, listContacts, listInsights. Counts at build: memories 1, captures 0, contacts 1, insights 2.
- BlueprintOS: supabase/schema.sql for project mjbbpzwyamymboazabmx (RLS enabled, service role only). Mirror auto-upserts to Supabase once the schema is applied; currently reports the actionable failure by design.
- Promote helper: src/ob_nucleus/promote.py (capture to explicit memories per conventions), gated behind --confirm, written and deliberately not executed.
- Read sweep: ob-nucleus sweep run. Executed once; digest in verification/read_sweep_2026-06-07.md.

## Verified

- Phase 1 smoke (brief 4.5): all five reads pass. Identity (userId, pat, scopes [read]), tier agency, credits 50000 of 50000, projects list, unread insights. Nucleus ENABLED. See verification/phase1_smoke.md.
- Unit tests: 10 of 10 pass (write guard refusal, credit reporting, error mapping, 429 retry exhaustion, token redaction).
- Live CLI reads: account credits, projects list, leads list, nucleus insights all return real data.
- Mirror builds from live reads; sync_runs audit row written; no live Nucleus write made.
- Secret scan of staged diff: clean. Em dash scan of authored files: clean.

## Brief vs API discrepancies (API wins, logged per guardrail 6)

1. GET /api/user/current returns no userEmail (brief 4.5 expects it). Live: userId, authMethod, authData only.
2. Insight model (brief 5.2): live returns insightType not type, content not body, adds context, priority, expiresAt, and has NO projectId field.
3. Lead model (brief 6.5 recipe): live has no surveyStatus. Conversion state lives in status, convertedToAuditId, conversionTimestamp. Live uses businessName, aiReadinessScore, compositeScore.
4. Memory model: live adds isArchived, isShared, teamId, sourceContext, sourceConversationId, lastRetrievedAt.
5. Contact model: live adds teamId, stakeholderId, leadSurveyId, updatedAt.
Code maps live shapes with brief-shape fallbacks; raw JSON is preserved in the mirror for full fidelity.

## Blockers and flags

1. Supabase BlueprintOS tables do not exist yet. PostgREST cannot run DDL with the service key; one paste of supabase/schema.sql in the SQL editor unblocks the full pipeline.
2. gh CLI auth on OB1AIRIG is broken (keyring failure for masterjedi-ob1). Clone worked; push path verified at commit time (see repo).
3. Security: ob-nucleus-env-keys.txt in the Drive OB-Nucleus folder holds six plaintext production secrets (Audity PATs, Notion token, Supabase keys). Recommend moving to the OB1-Brain token registry pattern (brief 4.3.4) and removing the file.
4. claude mcp list times out on OB1AIRIG due to the number of registered servers; claude mcp get audity is the reliable check.

## Next authorized actions (need Chris)

1. Apply supabase/schema.sql in the Supabase SQL editor (Dashboard, SQL Editor, paste, Run), then run: ob-nucleus mirror sync. NO CREDITS.
2. Org seat and token model decision per brief 4.3 (owning seat, per-agent PATs, rotation registry). NO CREDITS.
3. First gated write test: ob-nucleus nucleus capture-note --content "..." --confirm with AUDITY_WRITE_TOKEN, then promote dry run. NO CREDITS (captures and memories are free; rate limited 30/hr).
4. Lead conversion candidates from triage: GlobalTech Consulting (readiness 94), USI Insurance Services (92). COSTS 1000 CREDITS EACH, non-idempotent.
5. Schedule the daily read sweep (Cowork scheduled task or Task Scheduler calling ob-nucleus sweep run). NO CREDITS.
6. Merge chief/initial-build to main after review. NO CREDITS.

Rules before tools.

## Update 2026-06-07, evening

- Chris applied supabase/schema.sql via the SQL editor (success, no rows returned). Blocker 1 RESOLVED.
- ob-nucleus mirror sync pushed 4 rows to BlueprintOS. Verified in Postgres: nucleus_memories 1 (Athens Foods lead stage), nucleus_contacts 1, nucleus_insights 2 (both stale_client). Pipeline is now live end to end: Audity reads to SQLite to Supabase.
- Known gap: sync_runs audit rows are written to SQLite only; remote run logging to the Supabase sync_runs table is a small future enhancement.

## Update 2026-06-07, directives executed

- Seat decision (brief 4.3) CLOSED by Chris: OB.1 operates Audity on Chris's agency-level seat with per-agent tokens, Chief token active. No org account. Recorded in TOKEN_REGISTRY.md.
- Merged chief/initial-build to main (fast forward) and pushed.
- First gated write EXECUTED with approval: capture-note 422b17b4-6ca9-4ea8-91e7-b7139a4bf593 on the write token, extraction processed 5 items, promote dry run drafted 4 memories and wrote none. Write path verified end to end. Zero credits.
- GlobalTech conversion HELD by Chris after flags: contact email is test.analysis@example.com (seeded test lead pattern) and conversionTimestamp is populated with no audit ID. Conversion queue: GlobalTech (94, flagged), USI Insurance (92).
- Daily sweep SCHEDULED: Windows Task Scheduler task "OB1 Audity Daily Sweep", daily 07:00, runs scripts/daily_sweep.ps1 (read sweep + mirror sync + Drive copy). Next run 2026-06-08 07:00.
- Token hygiene DONE: plaintext key file retired from the Drive folder, all ten credentials preserved as OB1AIRIG user environment variables, redacted TOKEN_REGISTRY.md created per brief 4.3.4. Caveat: the retired file lived on a shared drive; revoke and reissue any token on suspicion of exposure.
- Credits at session end: 50000 of 50000. Zero spent across the entire build.
