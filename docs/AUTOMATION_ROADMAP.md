# OB.1 automation roadmap: workflows and the iterative loop

Version 1.0.0 (2026-06-07, Chief). Inputs: Chris's directives (Granola transcription pipeline, ReadyLink distribution, bilateral readiness tracking, Google Meet interview scheduling) plus everything built and verified in OB-Nucleus today. Companion to docs/PRD_OB1_REVENUE_LOOP.md.

Operating principle: every workflow below follows the same maturity ladder. Dry run (agent shows its work, human executes) to canary (agent executes a small approved batch) to default-on (agent executes, human reviews the digest). Nothing skips a rung. Credit spends and outbound sends never leave human approval.

## Tier 1: running today

W0. Daily read sweep and mirror sync. Task Scheduler 07:00, reads only, digest to Drive. Status: default-on since 6/7.

## Tier 2: next 30 days (highest leverage per hour invested)

W1. Granola to Nucleus transcription pipeline (Chris directive 1). The human stops ferrying meeting notes.
- Flow: daily 17:30 agent run lists the day's Granola meetings (Granola MCP is already org-connected), matches attendee email domains against revenue_xref to find the client and projectId, submits each transcript as a Nucleus capture-note (50k char chunks, project-linked), extraction auto-creates memories (verified behavior: captures seed memories without promote), agent curates which extracted facts become explicit memories per conventions, and queues a Notion Decisions Log row.
- Guards: 30 captures/hour ceiling governs batch size; client match below confidence threshold routes to a human pick-list instead of guessing; internal-only meetings are skipped by default.
- Metric: percent of client meetings captured within 24h (target 95), manual transfer minutes per week (baseline est. 60-90, target under 5).

W2. ReadyLink distribution through Pipeline (Chris directive 2a). The readiness assessment becomes the lead magnet.
- Flow: Audity ReadyLinks API (brief Section 7, feature-gated on multiReadyLink; verify gate on the agency tier before building) issues a tracked assessment link per campaign; the Outreach Steward injects it into Pipeline message templates at the interested stage; completions land as scored Audity leads and flow to Attio via the Scribe within 24h.
- Guards: one ReadyLink per campaign for attribution; link issuance is a write, gated behind confirm.
- Metric: assessment completion rate per campaign; scored-lead volume per week (baseline 0 automated).

W3. Bilateral readiness tracking (Chris directive 2b). One score, visible everywhere, tied to stage.
- Flow: ai_readiness_score lives on the Attio company record and as a Pipeline table column (PRD FR-CRM-001, FR-OUT-002); stage mapping runs both directions (Audity status to Attio stage, Attio stage changes back through the Loop Closer); a weekly reconciliation job diffs scores and stages across the three systems and flags drift in loop_events.
- Metric: drift incidents per week (target 0 sustained); time from score change to CRM visibility (target under 24h).

W4. Stakeholder interview scheduling (Chris directive 2c). The calendar Tetris disappears.
- Flow: when a project enters interviews stage (detected by the daily sync), the agent pulls stakeholder contacts, proposes interview slots from Chris's calendar (Google Calendar MCP suggest_time, already org-connected), drafts invites with Google Meet links and the stakeholder-specific briefing, sends after one-tap approval, books follow-ups for no-shows, and Granola auto-capture (W1) closes the loop from meeting to memory.
- Guards: outbound email and invites are always human-approved in v1; reschedules above 2 per stakeholder escalate to Chloe.
- Metric: days from interviews stage to all interviews booked (baseline manual, est. 5-10 days; target 2).

## Tier 3: 60-90 days

W5. Conversion queue with one-tap approval (PRD FR-LOOP-002): Audit-Ready leads queue with cost and balance; Chris approves in Slack or the morning digest; the convert fires gated and logs.
W6. Weekly Coach loop (modeled on Pipeline's Coach): every Monday the agent attributes outcomes (replies, bookings, conversions) to upstream choices (readiness threshold, opener variant, capture quality), proposes one parameter change, and applies it only after approval. The system tunes itself one variable at a time.
W7. Deliverables-to-client packaging: when an Audity analysis completes, auto-draft the OB.1-branded engagement summary from getDeliverables into the Client_SOW_Summary template for human polish. Reads only; drafting is free.

## The iterative optimization process (how we get faster, more accurate, more efficient)

1. Instrument first. Every agent run writes loop_events (already specced). No tuning without measurement.
2. One change per cycle. Weekly cadence; a single parameter moves (threshold, schedule, template); the digest reports the delta the following Monday.
3. Promote on evidence. A workflow climbs the maturity ladder (dry run, canary, default-on) only after 3 consecutive clean cycles at its current rung; any failure drops it one rung automatically.
4. Probe before parsing. Every new external surface gets a live-shape probe before code ships (the lesson from insightType, conversionTimestamp, and the docs-only MCP, all caught this way).
5. Quarterly hygiene. Token rotation per TOKEN_REGISTRY.md, connector re-qualification against vendor changes, schema drift audit, and a pruning pass that retires automations nobody reads.

| Dimension | Mechanism | 90-day target |
|---|---|---|
| Speed | Scheduled agents replace human ferrying (W0, W1, W4) | Lead-to-CRM under 24h; interviews booked in 2 days; meeting-to-memory same day |
| Accuracy | xref identity spine, drift reconciliation (W3), probe-first rule | 0 sustained drift; 0 duplicate records; API-verified shapes only |
| Efficiency | Gated writes with cost surfacing, one-variable tuning (W6) | 0 wasted credits; under 30 min/week human time on pipeline data work |

## Dependencies and sequencing

W1 needs: revenue_xref (PRD Phase A), Granola MCP scopes confirmed. W2 needs: ReadyLink tier gate verified, Pipeline campaign live (Matt). W3 needs: Attio lists (Chloe) plus Scribe deployed. W4 needs: calendar MCP write approval flow agreed with Chris. W5-W7 need: Phases A-C of the PRD complete. Recommended build order: W1 (standalone value, no external dependencies beyond Granola), then PRD Phase A, then W3, W2, W4 in parallel, then Tier 3.
