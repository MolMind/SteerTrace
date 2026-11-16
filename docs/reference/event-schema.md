# Analysis contract: steertrace.events/v1

The invoking agent authors the analysis. The CLI validates citations and structure,
not semantic truth. Start from the run's `events.template.json`. Read every evidence
packet, including late constraints and outcomes. Output one JSON object without
Markdown fences. Empty events/recommendations are valid.

## Analysis method

Before authoring findings, apply the [judgment analysis method](../../skills/steer-trace/references/analysis-method.md).
Reconstruct the problem and information available at the decision time; compare recorded
alternatives; separate decision quality, execution, and outcome; compare causal explanations.
Use the existing interpretation and uncertainty fields for relevant analysis, not a compulsory
checklist in every event. Semantically review main findings and directions before CLI validation.
Missing reasoning stays unknown; exact quotes alone do not establish adequate support.
Check the action status of consequential claims and the units, purpose and scope of numeric
criteria. Requests are not completed actions; rollback triggers are not automatically acceptance
thresholds. Preserve source qualifications in the claim itself. These checks use existing fields.

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
  "verification_signal": "In a comparable new task, a conclusion tied to agreed timing boundaries would support this direction; if a different bottleneck dominates, its applicability needs revision.",
  "status": "hypothesis"
}
```

New recommendations include non-empty `verification_signal`: an observable change in a
comparable future decision and evidence that would weaken or limit the direction.
`next_check` describes context and value; `verification_signal` makes effectiveness testable.
Agreement, adoption, and one successful outcome do not establish improvement. Older v1
recommendations without the field remain valid with a warning; a supplied empty or non-text
field is invalid. The validator cannot assess whether the signal is meaningful.

Prioritize by evidence strength, decision impact, and future reuse value without scoring people.
Directions can extend effective practices as well as address errors.
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

## 回应摘要与问题归因（兼容 v1 的增量字段）

新事件在存在 `after` 证据时提供 `ai_response`：概括 AI 公开表达的处理方式及
自报结果，保留“报告已完成”“待验收”等限定，不重建内部思考。无后续证据时省略。
提供该字段却缺少 `after` 引用会校验失败；旧事件仍可读取，以后续原话展示回应。
引用选取完整语义单位并保留相关限制，不使用孤立标题或截断半句。
短 AI 摘录会触发人工语义复核提示，不按字数判定证据真假。

新批评提供 `attribution`（`user`、`ai`、`shared`、`unknown`）及非空
`attribution_reason`。理由应与所引事件的原话、前后回应相符；分别表示用户判断、
AI 表达或执行、双方协作、归因未定。字段值不能代替因果证据。
旧批评缺失归因时保持有效并提示，页面显示“归因待核对”。
评估测试范围时核对原有轮数与执行授权，区分实现自动测试功能和立即运行测试。
出现停止指令不单独证明此前测试未经授权，也不证明已及时停止。

报告按原始对话顺序排列，使用消息源时间（Unix 秒/毫秒或带时区 ISO 8601），
统一显示 UTC+8；不使用报告生成时间代替事件时间。缺失、无时区、无效时间显示
“时间未记录”，异常顺序不重排对话。合并事件显示时间范围，原话保留逐条时间。
