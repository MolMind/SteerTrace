# Changelog

## Unreleased

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
