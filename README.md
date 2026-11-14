# SteerTrace

**Strengthen your thinking when working with AI by examining judgment, tracing errors, and grounding decisions in evidence.**

[中文](README.zh-CN.md) · [Documentation](docs/README.md) · [Skill](skills/steer-trace/SKILL.md)

## Overview

SteerTrace examines how you frame problems, evaluate AI suggestions, make tradeoffs,
and explain unexpected results. It connects those judgments to conversation evidence,
reveals gaps between assumptions and conclusions, and identifies reasoning worth
preserving or strengthening.

The result is an interactive HTML report: key findings, original dialogue, error
attribution, and concrete directions for strengthening your thinking.

## Quick start

Give your agent this prompt:

> Install the steer-trace Skill from https://github.com/MolMind/SteerTrace.
> Follow the repository's installation guide, adapt to this client, and handle
> the required setup and verification for me.

After installation, say:

> Analyze this conversation.

Or invoke `steer-trace` through your client's Skill mechanism. The agent handles
the workflow and delivers the report using these rules:

1. **Explicit target first:** a specified file or conversation takes precedence.
2. **Current conversation by default:** no path is needed for a normal invocation.
3. **Invocation excluded:** the triggering message and everything after it stay out of the analysis.
4. **Ask only when access is unavailable:** never guess another chat or reconstruct dialogue from summaries.

## What you get

- **Judgment evidence:** how goals, assumptions, and choices connect.
- **Error attribution:** which explanations have support and where reasoning overreaches.
- **Thinking-strengthening directions:** specific reasoning patterns grounded in this conversation.
- **A readable report:** expandable evidence, search, filters, and printing/PDF.

You can also name another conversation, provide a file, or specify project documents
as supporting evidence. See the [manual workflow](docs/guides/manual-workflow.md)
and [input formats](docs/reference/input-formats.md) for details.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Installation](docs/guides/installation.md) | Agent-managed setup and manual environment instructions |
| [Client integration](docs/guides/clients.md) | Current-session access across clients |
| [Manual workflow](docs/guides/manual-workflow.md) | Explicit files, project documents, and CLI commands |
| [Troubleshooting](docs/guides/troubleshooting.md) | Missing history, branches, and validation errors |
| [Technical documentation](docs/README.md) | Formats, analysis contract, architecture, and validation |

## Privacy and evidence

Only the current or explicitly selected conversation and specified documents are
analyzed. Reports can retain quotations and business content; review them before
sharing. Citation validation checks evidence correspondence, not whether every
interpretation is correct. Analysis concerns visible decisions, not personality.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [changelog](CHANGELOG.md).

## License

[MIT](LICENSE) · Copyright (c) 2026 SteerTrace contributors.
Bundled [Tabler Icons](https://tabler.io/icons) are also MIT-licensed;
[upstream notice](src/steertrace/assets/tabler-LICENSE.txt) is included.
