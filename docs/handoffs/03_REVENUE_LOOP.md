# HANDOFF Lane 3: revenue loop build (PRD OB1-INT-2606-001)

Paste into a fresh OB-Nucleus project chat. You are Chief, lane 3 of 6. Read first: handoffs/00_INDEX_THE_LARGER_PICTURE.md, docs/PRD_OB1_REVENUE_LOOP.md (the spec; it is complete), repo STATUS.md.

## Mission

Execute the PRD: three agents (CRM Scribe, Outreach Steward, Loop Closer) over BlueprintOS tying Audity intelligence to Attio (the live pipeline surface) and pipeline.help (Matt Vinall's GTM platform). Readiness scores ride on every record. Humans approve every send and every credit spend. This lane converts today's foundation into booked revenue motion.

## What exists and is verified

- The PRD is zero-ambiguity complete: architecture, 12 FRs with acceptance criteria, data specs (Attio attributes and stages, BlueprintOS tables, Pipeline payload), test strategy, deployment schedules, handoff matrix.
- Attio: workspace "OB.1 AI", Chris admin, ZERO lists today (greenfield; you and Chloe create the schema in PRD Section 6). Attio MCP tools are org-connected (create-record, update-record, search-records, create-task, list-lists, whoami all available).
- Pipeline: hosted MCP (87 tools), CLI pipeline-gtm, REST POST /api/v1/prospects. No OB.1 key provisioned yet. WARNING: the payload contract in PRD Section 6 came from marketing pages, not a live probe. Probe before parsing; fix the PRD if reality differs.
- Four blocking questions (PRD Section 10) are unanswered: Pipeline workspace owner, sending seat, readiness threshold (80 proposed), Attio stage names.

## Scope (yours)

1. Get the four blocking answers from Chris, Matt, Chloe. Update the PRD to 1.1.0 with the answers.
2. Phase A: Attio schema creation with Chloe, then build the CRM Scribe (idempotent upserts keyed on revenue_xref from lane 1's schema_v3). Canary: 3 records, Chloe verifies, then default-on daily 07:15.
3. Phase B: probe the live Pipeline API with Matt's key, then build the Outreach Steward (dry-run default; payload includes audity_readiness, audity_top_signal, audity_lead_url).
4. Phase C: Loop Closer (replies to Attio tasks + Nucleus captures; conversion_queue rows for Audit-Ready leads).

## Non-goals (other lanes)

schema_v3 authoring (lane 1 delivers it; you consume it). MCP server changes (lane 2). Granola transcripts (lane 6). Converting any lead without a conversion_queue approval from Chris.

## First three actions

1. Read the PRD end to end. Verify Attio is still greenfield (list-lists) and BlueprintOS row counts match STATUS.md.
2. Send Chris the four blocking questions as a one-screen ask with your recommendations.
3. Branch chief/lane-03-revenue-loop; scaffold src/ob_nucleus/agents/ with the Scribe skeleton and its dry run against live BlueprintOS rows.

## Definition of done

Scribe default-on with the active book visible in Attio; Steward producing approved dry-run payloads against a live Pipeline campaign; Closer specced and in canary; conversion_queue flowing to Chris. Metrics per PRD Section 1 table.

## Needs humans

Chris: blocking answers, canary approvals. Matt: Pipeline key + campaign. Chloe: Attio lists + canary verification. Credit spends: none until conversion approvals.
