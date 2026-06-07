# Nucleus taxonomy

Source: activation brief Section 5. One page for agents and for Andrew. When the live API disagrees with this page, the API wins; log the discrepancy in STATUS.md.

## Memory types (memoryType)

| Type | Meaning | projectId |
|---|---|---|
| client | A fact about one engagement | Required (OB.1 convention) |
| pattern | A reusable cross-client lesson | Never |
| preference | How OB.1 likes to work | Never |

Default when omitted: client.

## Memory source types (sourceType)

| Source | Meaning | Trust |
|---|---|---|
| explicit | Human or agent asserted on purpose; all API-created memories | Fact |
| extracted | Pulled from a capture by the extraction job | Trust but verify |
| detected | Hypothesis from a background job | Lead, weigh confidence |

## Capture channels (8 total; API creates only text_note in v1)

| Channel | Populated by |
|---|---|
| text_note | Agent API (POST /api/nucleus/capture/note) |
| transcript | Audity integrations |
| voice_note | Audity integrations |
| email | Audity integrations |
| calendar | Audity integrations |
| zoom | Audity integrations |
| crm_sync | Audity integrations |
| file_drop | Audity integrations |

## Capture statuses

pending, processing, processed, needs_review, failed. Extraction runs asynchronously, roughly 15 to 60 seconds. On failed, reprocess via POST /api/nucleus/captures/{id}.

## Insight types: live vs reserved (v1)

| Type | Status | Meaning |
|---|---|---|
| overdue_followup | LIVE | A follow-up whose date has passed |
| pattern_detected | LIVE | A cross-client pattern in the portfolio |
| similar_lead | LIVE | A new lead matches a past project profile |
| stale_client | LIVE | A client quiet long enough to risk going cold |
| pre_meeting | reserved | In schema, not yet produced |
| referral_opportunity | reserved | In schema, not yet produced |
| portfolio_insight | reserved | In schema, not yet produced |
| content_suggestion | reserved | In schema, not yet produced |

Never promise reserved types to clients.

## Contact relationship types

client, prospect, partner, referral. Anything else is silently coerced to null by the API.
