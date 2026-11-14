# Analysis contract: steertrace.events/v1

The invoking agent authors the analysis. The CLI validates citations and structure,
not semantic truth. Start from the run's `events.template.json`. Read every evidence
packet, including late constraints and outcomes. Output one JSON object without
Markdown fences. Empty events/recommendations are valid.

## Root fields

| Field | Requirement |
| --- | --- |
| `schema_version` | Exactly `steertrace.events/v1` |
| `run_id` | Exact ID from the frozen run manifest |
| `events` | Array of judgment-event objects |
| `recommendations` | Array of 0–3 recommendations |
| `limitations` | Non-empty array of strings describing actual limitations |

## Event fields

| Field | Requirement |
| --- | --- |
| `id` | Unique non-empty string; use E1, E2, etc. |
| `kind` | goal, question, critique, constraint, tradeoff, selection, authorization, stop |
| `summary` | Concise observed action; do not put an unsupported accusation in the title |
| `ownership` | human_proposed, ai_proposed_human_selected, authorization_only, unknown |
| `evidence_posture` | observed_submission, contextual_inference, unknown |
| `user_evidence` | Non-empty array of eligible user references |
| `before` | Array of assistant references preceding the user event; may be empty |
| `after` | Array of assistant references following the user event; may be empty |
| `interpretation` | Your explanation, explicitly separate from original evidence |
| `uncertainty` | What cannot be concluded, not a generic confidence number |
| `document_links` | Array of exact document associations; may be empty |

Each message reference is `{"message_id":"u1","quote":"exact substring"}`.
Use IDs and text from `conversation.json`, after normalization and redaction.
Different chunks of a long message retain the same ID; deduplicate overlapping
events. A source ID is not a timestamp or a raw file line number.

Before references must be earlier than all cited user messages; after references
must be later. For decisions unfolding across several turns, use separate events
rather than pretending an interleaved dialogue is one instantaneous decision.

`human_proposed` means the user submitted the proposal in this conversation, not
that they invented it without AI. AI-proposed/human-selected requires a preceding
assistant proposal. Bare acknowledgments cannot establish proposal ownership.
Unknown submission envelopes are not eligible for user evidence.

Example document association:

```json
{
  "doc_id": "d1",
  "quote": "exact text in documents.json",
  "relation": "records_matching_constraint",
  "verification": "documented"
}
```

Relations: `records_matching_constraint`, `records_plan`, `reports_result`.
Verification: `documented`, `reported_result`, `unknown`. None means independent
reproduction. A matching statement does not prove a unique causal connection.
Do not fabricate an old document version from the current file. If no document
association is supported, leave the list empty and describe the limitation.

## Recommendations

```json
{
  "event_ids": ["E1"],
  "text": "Anchor latency comparisons in consistent measurement boundaries.",
  "next_check": "When comparing options, agreed timing boundaries make the latency evidence comparable.",
  "status": "hypothesis"
}
```

Describe a concrete reasoning direction and its value at an actual decision point. Do not add a suggestion
just to fill a quota. Do not infer stable personal traits from a single session.

See [the public synthetic analysis](../../examples/synthetic/analysis.json) for a full
example. Its run_id placeholder is replaced by the demo only; it is not an
autonomous extraction benchmark.

## Frozen evidence

Run hashes bind analysis to normalized conversation and document snapshots.
User/document quotes must match those snapshots character-for-character. The
document's own SHA-256 records original file bytes; its text may be redacted, while
the run-level document digest binds the actual redacted snapshot. Current document
links can drift after editing; re-prepare for a new evidence version.

Validation does not protect against a malicious actor rewriting both snapshots
and the manifest. There is no cryptographic signature or verified human identity.

## Human-facing review and criticisms

New analyses include these root fields. Older analyses without them remain valid;
rendering uses a neutral introduction and does not manufacture criticism.

```json
{
  "review": {
    "headline": "目标取舍清晰，能力判断仍缺少独立证据",
    "summary": "用具体事实说明本次的主要发现。",
    "keep_doing": ["本次证据支持、值得延续的思维方式。"]
  },
  "criticisms": [{
    "event_ids": ["E5"],
    "basis": "observed_instance",
    "title": "样本表现与通用能力之间存在证据缺口",
    "problem": "具体哪条判断站不住，为什么。",
    "consequence": "这样做可能带来的代价，不把风险写成已发生的结果。",
    "better_move": "结合本次证据，描述更有依据的思维路径，避免命令口吻。"
  }]
}
```

`review` requires non-empty `headline` and `summary`, plus a `keep_doing` text array
(empty is valid). `criticisms` may be empty. Each criticism requires non-empty
fields shown above and references to existing events. `basis` is
`observed_instance` or `inference`; inferred criticisms are labeled in the report.
Citation checks cannot determine whether a criticism is fair. The agent must
consider context, later corrections, and counterevidence; never force a quota.

All displayed text follows the [report style contract](../../skills/steer-trace/references/report-style.md).
Use plain language. Firm criticism of a specific judgment is encouraged when
supported. Personality labels, presumed motives, intelligence ratings, invented
outcomes, and source IDs embedded in prose do not belong in the report.

## Presentation tone

Recommendations are thinking-strengthening directions, not instructions to the reader.
`text` names a concrete reasoning direction; `next_check` describes its value in a
specific decision context. Apply this tone to `better_move` and `keep_doing` too.
Keep `uncertainty` and `limitations` in analysis JSON; the report omits their standalone
sections. Material qualifications belong in the finding they affect. See the
[report style contract](../../skills/steer-trace/references/report-style.md).
