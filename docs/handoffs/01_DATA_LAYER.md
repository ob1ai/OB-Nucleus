# HANDOFF Lane 1: BlueprintOS data layer steward

Paste into a fresh OB-Nucleus project chat. You are Chief, lane 1 of 6. Read first: handoffs/00_INDEX_THE_LARGER_PICTURE.md, repo STATUS.md, repo CLAUDE.md.

## Mission

BlueprintOS (Supabase mjbbpzwyamymboazabmx) is OB.1's sovereign data layer: the single queryable surface for active client work, pipeline intelligence, and Nucleus memory. You own its schema evolution, sync integrity, and the rule that it never drifts from Audity (the source of truth). Mirror, do not fork.

## What exists and is verified

- src/ob_nucleus/mirror.py syncs 6 entity tables from live Audity reads into SQLite (everything) and Supabase (active clients only via OBN_SYNC_SCOPE=active: status past setup, not archived, no sandbox names).
- supabase/schema.sql and schema_v2.sql are applied. Verified rows: 7 active projects, 53 leads, memories, contacts, insights.
- Daily sweep (07:00 Task Scheduler) runs sweep + mirror sync unattended.
- Known gap: sync_runs audit rows write to SQLite only, not Supabase.
- DDL path: service key cannot run DDL. Schema changes ship as numbered supabase/schema_vN.sql files, posted inline to Chris for a one-paste SQL-editor run. A Supabase management token (sbp_) or DB password in OB1AIRIG user env would remove this roundtrip; ask Chris if he wants to store one.

## Scope (yours)

1. Author supabase/schema_v3.sql: revenue_xref, loop_events, conversion_queue exactly as specced in docs/PRD_OB1_REVENUE_LOOP.md Section 6. Post inline to Chris for paste.
2. Wire sync_runs remote logging into _push_supabase so every sync is auditable in Postgres.
3. Add a drift check to the daily sweep: counts and freshness per table, SQLite vs Supabase vs live API, flag anomalies in the digest.
4. Own data quality: the duplicate Cleveland Candy pair, test-rig exclusion list maintenance, soft-delete semantics when Audity archives projects mid-cycle (observed live on 6/7: statuses flip to archived between reads; the filter handles it, the purge of stale Supabase rows is yours to automate).

## Non-goals (other lanes)

Attio or Pipeline writes (lane 3). MCP server changes (lane 2). Granola captures (lane 6). Human training (lane 4).

## First three actions

1. Run ob-nucleus mirror status and a Supabase row-count probe; confirm ground truth still holds.
2. Author schema_v3.sql and hand it to Chris inline.
3. Patch mirror.py for remote sync_runs; test; commit on chief/lane-01-data-layer.

## Definition of done

schema_v3 applied and populated by lane 3's agents; sync_runs visible in Supabase; drift section appears in the daily digest; STATUS.md lane update written.

## Needs humans

Chris: schema_v3 paste (no credits); optional sbp_ token decision. Nothing else.
