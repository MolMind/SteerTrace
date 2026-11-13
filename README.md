# SteerTrace

**Examine how you judge AI advice, reason about errors, and improve your next decision.**

SteerTrace is a Skill for analyzing judgment and error attribution when working
with AI. Using selected agent conversations and project documents, it examines
how you frame problems, evaluate suggestions, make tradeoffs, and explain or
correct errors. It connects decisions to their stated evidence, identifies where
inferences exceed that evidence, and presents directions for strengthening
judgment in an HTML report.

[中文说明](docs/README.zh-CN.md) · [Judgment Analysis Skill](skills/collaboration-judgment-review/SKILL.md) ·
[Input formats](docs/input-formats.md) · [Analysis contract](docs/event-schema.md)

## Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements and installation](#requirements-and-installation)
- [Quick start](#quick-start)
- [Use with Codex and other clients](#use-with-codex-and-other-clients)
- [Review your conversation](#review-your-conversation)
- [Evidence and privacy](#evidence-and-privacy)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development and contributing](#development-and-contributing)
- [License](#license)

## Overview

Every choice to accept an answer, reject a proposal, request a change, or confirm
a result involves human judgment. SteerTrace focuses on the evidence and reasoning
behind those choices, especially how you infer a cause when results go wrong.

- **Problem framing:** Were goals, constraints, and acceptance criteria explicit?
- **Evaluating advice:** What supported acceptance or rejection? Was confidence,
  a local success, or an unverified claim treated as sufficient evidence?
- **Error attribution:** Can the evidence distinguish possible sources such as
  requirements, human decisions, AI output, and execution conditions? Was a cause
  assigned too early?
- **Revising judgments:** Which assumptions changed with new evidence, and what
  should be checked at the next decision point?

For example, a passing sample may not support a claim of general reliability.
Likewise, blaming a failure on model capability requires examining whether
ambiguous requirements, missing inputs, or execution conditions remain plausible
explanations. Where the cause is unresolved, the analysis preserves uncertainty.

The analysis uses visible conversation and document evidence. It does not recover
unspoken thoughts, infer causality from sequence alone, assess personality or
intelligence, or infer lasting habits from one session.

SteerTrace combines a local Python CLI with an agent Skill. The CLI imports and
freezes evidence, validates citations, and renders reports. The invoking agent
performs the analysis. No separate model API key is required. The current release
is 0.1.0; it does not include an MCP server or a client plugin.

## Features

- Trace goals, assumptions, and choices to stated evidence and later responses.
- Examine which error attributions are supported, inferred, or unresolved.
- Identify specific reasoning problems, their possible cost, and better actions
  without forcing findings when evidence is insufficient.
- Highlight effective reasoning and up to three directions for strengthening
  judgment, grounded in specific decision contexts.
- A consistent, responsive layout with search, filters, and printing/PDF support.

The report contains a scrollable reading guide, a core conclusion, judgment and
attribution findings, quoted evidence, and thinking-strengthening directions.
Its restrained layout uses rounded surfaces and whitespace. Desktop scrolling
and step buttons navigate the guide; mobile uses step buttons. Native evidence
disclosures support pointer and keyboard interaction. Reduced-motion preferences
are respected, and report content remains readable without JavaScript.

Uncertainty and coverage details remain in the analysis artifacts. Material
qualifications are integrated into the relevant finding rather than separate
report sections.

Reports are self-contained HTML files: no server, external fonts, or chart service
is needed to read them. Internal evidence IDs stay in the analysis files.

## Requirements and installation

Python 3.9+ and pip are required; there are no runtime third-party dependencies.
Use a client that can read local files and execute shell commands for the full
agent workflow. Clone the repository and install from source:

```bash
git clone https://github.com/MolMind/SteerTrace.git
cd SteerTrace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
For a source checkout without installation, use
`PYTHONPATH=src python3 -m steertrace` on macOS/Linux.

## Quick start

After installation, run the synthetic demo:

```bash
python scripts/demo.py runs/demo
```

Open `runs/demo/report.html` in a browser. The example uses synthetic conversation
and hand-authored analysis to demonstrate the report and checks. Choose a new
output directory when repeating it; existing artifacts are never overwritten.

## Use with Codex and other clients

Open the repository in Codex or another agent client with local file and shell
access. Ask it to read `skills/collaboration-judgment-review/SKILL.md` and follow
that workflow. For example:

> Use skills/collaboration-judgment-review/SKILL.md to review the conversation
> export at /path/to/session.jsonl against /path/to/project and the documents
> docs/plan.md and docs/results.md. Use this checkout's .venv/bin/steertrace
> and write the report to runs/review-001/report.html.

Use absolute paths when the client works outside this checkout. On Windows the
virtual environment command is `.venv\Scripts\steertrace.exe`. The Skill's
relative references must remain available with the repository; copying only
SKILL.md is insufficient. This explicit-file workflow needs no client-specific
Skill installation and does not automatically discover all chat histories.

An MCP-only client needs an additional MCP adapter, which this repository does
not currently provide. A chat-only client requires you to run the CLI manually
and transfer the prepared evidence and analysis between steps.

## Review your conversation

```bash
steertrace import --input /path/to/session.jsonl --source auto \
  --output runs/conversation.json

steertrace prepare --conversation runs/conversation.json \
  --project /path/to/project --docs docs/plan.md docs/results.md \
  --output runs/review-001
```

Ask your agent to use [the review Skill](skills/collaboration-judgment-review/SKILL.md),
read `runs/review-001/ANALYZE.md` and all numbered evidence packets, and write
`events.json` using the supplied template. Your current agent performs the
analysis; the CLI prepares the material and checks the result without calling
another model or requiring an API key.

```bash
steertrace validate --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/validation.json

steertrace report --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/report.html
```

The Skill specifies the report's wording and sections; the packaged HTML renderer
controls its layout and interactions. See the [report style contract](skills/collaboration-judgment-review/references/report-style.md).

## Evidence and privacy

Supported inputs are generic role-labeled JSON, selected Codex JSONL, and basic
parent-linked Claude Code JSONL. Branches and incomplete histories need explicit
handling; see [format details](docs/input-formats.md).

Only selected exports and documents are read. Run directories are private by
default and excluded from Git. Credential redaction is best-effort; review the
report before sharing because quotations and business content may remain. When
your agent reads the material, its host/provider's data policies apply.

Quotes, roles, event order, and document matches are checked against frozen
snapshots. These checks do not prove that the analysis is correct, that a plan
worked, or that a recommendation will help. The report distinguishes proposals,
choices, permission to continue, and unknown attribution. Missing records are not
evidence of missing thought.

## Project structure

```text
src/steertrace/                       CLI, importers, validation, and HTML assets
skills/collaboration-judgment-review/ Agent instructions and report style
scripts/demo.py                      Synthetic end-to-end example
examples/synthetic/                  Invented conversation and analysis fixtures
tests/                               Importer and pipeline tests
docs/                                Input formats, schemas, and architecture
runs/                                Local output, excluded from Git
```

## Troubleshooting

- Command not found: activate the virtual environment or invoke
  `.venv/bin/steertrace` directly (`.venv\Scripts\steertrace.exe` on Windows).
- Existing output: choose a new output file or run directory; artifacts are not
  overwritten.
- Ambiguous Claude branches: import with `--leaf-id <uuid>` to select a branch.
- Incomplete input: inspect the coverage warning first. Use `--allow-partial`
  with `prepare` only when the disclosed missing history is acceptable.
- Validation failure: correct the analysis against the frozen evidence; do not
  edit source snapshots to make citations pass.

Run `steertrace --help` or `steertrace <command> --help` for command options.
See [input formats and limits](docs/input-formats.md) for unsupported exports.

## Development and contributing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python scripts/demo.py runs/another-demo
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution checks and fixture rules.
Use synthetic examples in bug reports; include the command, Python version, and
error without private transcripts or credentials.

Further reading: [Changelog](CHANGELOG.md) · [Validation](docs/implementation-validation.zh-CN.md) ·
[Architecture](docs/architecture.zh-CN.md) ·
[Analysis contract](docs/event-schema.md) ·
[Report style](skills/collaboration-judgment-review/references/report-style.md).

## License

SteerTrace is distributed under the [MIT License](LICENSE).
Copyright (c) 2026 SteerTrace contributors. You may use, modify, and distribute
it, including commercially, subject to preserving the copyright and permission
notice. The software is provided without warranty; see LICENSE for full terms.

Bundled SVG icons are from [Tabler Icons](https://tabler.io/icons) under MIT.
Their [upstream notice](src/steertrace/assets/tabler-LICENSE.txt) is shipped with
the package and embedded in generated reports.
