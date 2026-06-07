# QUICKREF: Audity agent surface

Distilled from the activation brief Sections 7 and 8. The brief is the spec; this is the lookup card. When this card and a live response disagree, the response wins.

Base URL: `https://app.auditynow.com`. Auth: `Authorization: Bearer aky_<token>`. JSON on writes.

## PAT route allowlist (v1)

Anything outside this list returns `403 PAT_ROUTE_NOT_ALLOWED`.

### Account
| Operation | Method and path | Notes |
|---|---|---|
| getCurrentUser | GET /api/user/current | Identity check, run at session start |
| getCurrentTier | GET /api/user/tier | Source of truth for gating |
| getCredits | GET /api/user/credits | Always check before credit-spending writes |

### Projects and audits
| Operation | Method and path | Notes |
|---|---|---|
| listProjects | GET /api/projects | |
| createProject | POST /api/projects | COSTS 1000 CREDITS |
| getProject | GET /api/projects/{id} | Includes documents |
| patchProject | PATCH /api/projects/{id} | |
| triggerAuditAnalysis | POST /api/projects/{id}/audit-analysis | Synchronous, 60 to 300s, costs credits |
| getAuditAnalysis | GET /api/projects/{id}/audit-analysis | Latest analysis |
| triggerAsyncAuditAnalysis | POST /api/agent/projects/{id}/audit-analysis/async | Needs current doc + interview analyses (else 422) |
| getJobStatus | GET /api/agent/jobs/{id} | Poll pending/processing/completed/failed |
| listOpportunities | GET /api/projects/{id}/opportunities | |
| getDeliverables | GET /api/projects/{id}/deliverables | Wrapped {success, data}; 404 until an analysis has run |

### Leads
| Operation | Method and path | Notes |
|---|---|---|
| listLeads | GET /api/lead-generation/leads | Wrapped {data, pagination, filters}; no since param, filter client side |
| getLead | GET /api/lead-generation/leads/{id} | |
| convertLead | POST /api/lead-generation/leads/{id}/convert | COSTS 1000 CREDITS, non-idempotent, 400 if already converted |

### Nucleus
| Operation | Method and path | Notes |
|---|---|---|
| listMemories | GET /api/nucleus/memories?type=&projectId= | Types: client, pattern, preference |
| createMemory | POST /api/nucleus/memories | {subject, content, memoryType, projectId}; 201 |
| updateMemory | PATCH /api/nucleus/memories | ID in BODY: {memoryId, subject?, content?} |
| deleteMemory | DELETE /api/nucleus/memories/{id} | Preferred path form; soft delete; idempotent 204 |
| listCaptures | GET /api/nucleus/captures?channel=&status=&projectId= | Wrapped {captures} |
| getCapture | GET /api/nucleus/captures/{id} | Returns {capture, items} |
| createCaptureNote | POST /api/nucleus/capture/note | {content <= 50000 chars, projectId?}; 30/hr; async extraction 15 to 60s |
| reprocessCapture | POST /api/nucleus/captures/{id} | Resets to pending |
| deleteCapture | DELETE /api/nucleus/captures/{id} | Soft delete, idempotent |
| listContacts | GET /api/nucleus/contacts?search= | Wrapped {contacts}; search matches name + company |
| createContact | POST /api/nucleus/contacts | Only name required; returns contact UNWRAPPED |
| updateContact | PATCH /api/nucleus/contacts | ID in BODY: {contactId, ...} |
| deleteContact | DELETE /api/nucleus/contacts | ID in BODY: {contactId}; HARD delete |
| listInsights | GET /api/nucleus/insights?type=&unreadOnly=&limit=25 | |
| getSuggestions | GET /api/nucleus/suggestions?projectId= | Returns 3 prompt strings |

### ReadyLinks and assessment configs (feature gated)
GET/POST/PATCH/DELETE under `/api/agent/readylinks` and `/api/agent/assessment-configs`.

### Browser only (PAT returns 403 PAT_NOT_SUPPORTED_FOR_ENDPOINT)
`/api/user/api-keys` (PAT management). PATs cannot manage PATs.

## Response shape traps

1. Contacts: UNWRAPPED on create, wrapped {contacts} on list.
2. Memory and contact update/delete pass the ID in the BODY, except the preferred path-form memory delete.
3. Deliverables wrap as {success, data}; leads wrap as {data, pagination, filters}; captures wrap as {captures}.
4. getDeliverables returns 404 until synthesis has run at least once.

## Error codes

| Status | Code | Meaning | Action |
|---|---|---|---|
| 400 | EMPTY_PATCH, DESCRIPTION_TOO_LONG, INVALID_DESCRIPTION_TYPE | Validation failed; also lead already converted | Fix body; skip converted leads |
| 401 | PAT_MALFORMED | Token format invalid, usually doubled Bearer prefix | Header exactly `Bearer aky_<token>`; regenerate if needed |
| 401 | (none) | Token revoked, expired, or never existed | New token |
| 402 | | Insufficient credits | Check GET /api/user/credits; top up |
| 403 | PAT_SCOPE_INSUFFICIENT | Token missing write scope | Reissue with write |
| 403 | PAT_ROUTE_NOT_ALLOWED | Route not on allowlist | Use the web app |
| 403 | PAT_NOT_SUPPORTED_FOR_ENDPOINT | PAT hit browser-only route | Use the browser |
| 403 | (tier, has requiredTier + upgradeUrl) | Plan lacks feature | Upgrade |
| 403 | (on Nucleus, not a scope code) | Nucleus disabled for account | Check account flag |
| 404 | | Not found or not owned (RLS) | Check ID and ownership |
| 409 | | Active token cap (10) reached | Revoke an old token |
| 413 | | Content too large | Reduce input |
| 422 | | Missing prerequisite analyses (async audit) | Use sync endpoint |
| 429 | | Rate limited; Retry-After header in seconds | Back off and retry |
| 503 | PAT_DISABLED | Agent API kill switch off | support@auditynow.com |

## Rate limits (per token)

| Class | Limit |
|---|---|
| Standard reads | 100 / minute |
| Writes | 20 / minute |
| Job polling | 120 / minute |
| Capture submissions | 30 / hour |
| Audit synthesis | Lower internal guardrails |

## Credit costs

| Operation | Cost |
|---|---|
| createProject | 1000 |
| convertLead | 1000 |
| triggerAuditAnalysis | Varies by depth |

## Insight types: live vs reserved (v1)

LIVE: overdue_followup, pattern_detected, similar_lead, stale_client.
RESERVED (in schema, not generated): pre_meeting, referral_opportunity, portfolio_insight, content_suggestion. Do not promise reserved types to clients.
