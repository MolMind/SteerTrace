# Changelog

## Unreleased

- Check action status and numeric criterion purpose/scope before consequential claims;
  distinguish requests from execution and rollback triggers from acceptance standards.
- Freeze direction applicability and anonymized task mappings before evaluation,
  support repeated paired comparisons, and report omissions separately from appropriate empty directions.
- Add twelve new sixteen-message cases with six strict single-message evidence pairs
  for before/after/generic repeated evaluation.

- Add 24 synthetic output-quality cases across eight families with eight minimal
  evidence pairs, family-separated dev/holdout groups, and seven quality dimensions.
- Add offline preparation, anonymized review and paired quality summaries for generic
  review, current core instructions and a pinned MIT session-review adaptation.
  Keep subjective semantic ratings separate from structural test results.

- Add decision-time evidence reconstruction, alternative-cause comparison, and semantic
  review checkpoints to the Skill and generated analysis instructions.
- Add observable verification signals to new directions, preserving legacy v1 analyses
  with a warning; display signals and avoid counting inferred criticisms as proven errors.
- Add synthetic judgment regression cases and manual semantic review criteria.

- Simplify the READMEs around thinking-strengthening value and agent-managed setup;
  group installation, client integration, reference, and development docs by purpose.

- Align the Skill name and directory with the project brand: `steer-trace`.

- Default Skill invocations to the current conversation, with explicit targets taking precedence.
- Add `capture` with exact invocation cutoff, identified Codex/Claude file resolution,
  and conservative DeepSeek Harness append-event import.
- Document native history/export acquisition and fail clearly when the host does
  not expose original history; never guess the latest transcript.

## 0.1.0 — 2026-11-13

Initial release of SteerTrace: a Skill and local Python CLI for examining judgment
and error attribution when working with AI.

- Import selected generic JSON, Codex JSONL, and basic Claude Code JSONL exports.
- Freeze explicit project documents and prepare evidence packets for the invoking agent.
- Validate quotes, roles, event order, attribution conditions, and document references.
- Render a self-contained HTML report covering judgment, attribution, and directions
  for strengthening reasoning, with rounded surfaces and a restrained palette.
- Include a scrollable reading guide, search, filters, native evidence disclosures,
  mobile layouts, reduced-motion support, and printing/PDF.
- Provide English and Chinese setup guidance, synthetic examples, and an MIT license.

The CLI does not call a model. An agent authors the analysis; citation validation
does not establish semantic accuracy. This version provides no MCP server,
automatic account-history collection, or client plugin.
