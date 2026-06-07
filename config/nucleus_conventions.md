# OB.1 Nucleus conventions

Source: activation brief Section 5.9. These rules keep Nucleus aligned with the Notion 6 database spine (Companies, Contacts, Deals, Engagements, Tasks, Decisions Log) and the OB1-Brain vault. Every agent that writes memory follows them.

## Writing rules

1. Subjects are addressable. Lead a client memory subject with the client name exactly as it appears in the Notion Companies database. Example: "Berman Killeen: HIPAA scoping status". Lead a pattern with its domain. Example: "Pattern: forensic psychology automation phasing".

2. One fact per memory. If the content has two clauses joined by "and", it is two memories. Findable beats comprehensive.

3. projectId is mandatory for client memories. Resolve the Audity project ID once per engagement and reuse it. Pattern and preference memories never carry a projectId.

4. Promote, do not duplicate. The pipeline is: transcript enters as a capture, the extraction job distills it, the distilled decision becomes an explicit memory and a row in the Notion Decisions Log. Never paste a whole transcript into a memory. The promote helper (`ob-nucleus nucleus promote <capture-id>`) implements this and is gated behind --confirm.

5. No em dashes, ever, including inside memory content. OB.1 writing rule.

6. Mirror, do not fork. Nucleus is the readiness and discovery memory; Notion remains the system of record for deals and engagements. When the two could drift, Notion wins and Nucleus is updated to match.

## Trust model when reading memory

- explicit: asserted on purpose by a human or agent. Highest trust; treat as fact.
- extracted: pulled from a capture by the extraction job. Trust but verify.
- detected: a background job hypothesis. Treat as a lead, not a fact; weigh confidence.

When informing a deliverable, prefer high confidence explicit memories as ground truth and label detected content as hypothesis.

## Memory hygiene (Anthropic principles applied)

- Memory is for continuity, not a dumping ground. Store decisions, durable facts, stable preferences. No transient chatter.
- Nothing sensitive that should not resurface unprompted in a future session.
- Keep memories concise and self contained so they read well out of context.
