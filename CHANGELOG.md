# Changelog

## 0.2.1

- Run the macOS installation check on the supported Intel runner to avoid arm64 capacity failures.

- 明确已有有效做法与新增建议的边界，提供具体检查意见并保留归因和证据限定；事件格式兼容，旧版仍受支持，不强制升级。

- Separate evidenced existing strengths from incremental advice; keep completed checks
  in strengths unless a stated new condition changes the decision evidence needed.
- Add completed, unresolved and changed-scope report regression examples; preserve
  the v1 event format and historical evaluation artifacts.

- Align reviews with idea-to-delivery collaboration: inspect AI proposals behind user
  decisions, surface consequential omissions, and offer concrete questions and checks
  without inferring hidden thought or assigning AI mistakes to the user.
- Allow actionable advice in existing report fields; add six complete synthetic
  collaboration cases and frozen before/after prompts, without claiming quality gains
  from structural regression tests or prepared evaluation tasks.

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


## 0.2.0

- Automatically tag and publish tested default-branch updates; safely skip exact release reruns.

- Display the generator version in the HTML footer and metadata; verify it against the CLI on installation.

- Add a single version source, release policy, Agent publishing rules and tag-based Release assets.
- Add cached stable-version checks and isolated managed upgrades with digest verification,
  local-modification protection, failed-update recovery and minimum-version enforcement.
- Add problem attribution, AI response summaries, source timestamps and clearer report typography.
- Existing versions remain supported; this release does not require a mandatory upgrade.

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
