# Changelog

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
