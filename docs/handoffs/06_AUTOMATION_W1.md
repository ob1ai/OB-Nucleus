# HANDOFF Lane 6: automation, W1 first (Granola to Nucleus)

Paste into a fresh OB-Nucleus project chat. You are Chief, lane 6 of 6. Read first: handoffs/00_INDEX_THE_LARGER_PICTURE.md, docs/AUTOMATION_ROADMAP.md (the plan; W1 through W7 with guards and metrics), repo STATUS.md.

## Mission

Build the automations that remove human ferrying from the flywheel, starting with W1: meeting conversations flow from Granola into Nucleus captures without anyone copying text, ever again. Then climb the roadmap (W2 ReadyLinks, W3 readiness tracking, W4 Meet scheduling) on the maturity ladder: dry run, canary, default-on. Nothing skips a rung; any failure drops a rung.

## What exists and is verified

- docs/AUTOMATION_ROADMAP.md: complete workflow specs with triggers, guards, metrics, and the iterative optimization process (one change per cycle, promote on 3 clean cycles, probe before parsing, quarterly hygiene).
- Granola MCP is org-connected (tools include list_meetings, get_meeting_transcript, query_granola_meetings). Shapes are UNPROBED; probe before parsing.
- Verified Nucleus behavior: POST capture-note triggers async extraction (15-60s) that auto-creates extracted memories; promote (gated, src/ob_nucleus/promote.py) is curation, not the only memory path. Capture ceiling: 30/hour. Content cap: 50k chars.
- Capture writes are live Nucleus writes: gated behind --confirm and AUDITY_WRITE_TOKEN. The standing approval pattern from 6/7 covers capture-notes for client meetings once Chris blesses the W1 canary; get that blessing explicitly.
- W1 does not need revenue_xref to start: match meetings to clients by attendee email domain against audity_projects/audity_leads in BlueprintOS; below-threshold matches go to a human pick-list, never a guess.

## Scope (yours)

1. Probe Granola MCP: list a real week of meetings, inspect transcript shape and attendee fields, document in the roadmap.
2. Build W1 as src/ob_nucleus/agents/granola_pipeline.py plus a scheduled task (17:30 weekdays): match, chunk, capture (gated), poll extraction, draft promote plan, queue the Notion Decisions Log line. Dry run first, then a 3-meeting canary Chris approves, then default-on after 3 clean days.
3. Instrument: every run logs to loop_events (lane 1 ships the table; until then, log to a local JSONL with the same shape).
4. After W1 reaches canary: spec-probe W2 (verify the ReadyLink tier gate on the agency plan with a live GET) and W4 (Google Calendar MCP suggest_time shapes). W3 belongs to lane 3's Scribe; coordinate via STATUS.md only.

## Non-goals (other lanes)

Attio/Pipeline agents (lane 3). Schema authoring (lane 1). Anything that sends external email or invites without approval (W4 sends are human-approved in v1 by design). No transcript content in git, logs, or STATUS.md; reference meetings by date and matched client only.

## First three actions

1. Probe Granola: one real meeting end to end (list, fetch transcript, inspect attendees). Document shapes.
2. Write the matching logic against BlueprintOS and dry-run it on the last 5 client meetings; show the match table.
3. Branch chief/lane-06-automation; commit the dry-run pipeline; request W1 canary approval from Chris with the 3 meetings named.

## Definition of done

W1 at canary or better with 95% of client meetings captured within 24h over a test week; manual transfer minutes near zero; W2 and W4 probes documented; STATUS.md lane update written.

## Needs humans

Chris: W1 canary blessing (captures are free; rate-limited 30/hr), W4 approval flow design. Privacy call on internal-only meetings stays default-skip.
