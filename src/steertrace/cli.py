"""Local-only command line. Semantic work belongs to the invoking agent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .importer import import_conversation
from .capture import capture, locate
from .pipeline import prepare
from .report import render
from .storage import TraceError, read_json, write_json, write_text
from .validation import validate


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="steertrace", description="Evidence-linked reviews of human judgment in agent-assisted work.")
    cli.add_argument("--version", action="version", version=__version__)
    commands = cli.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import", help="Import one explicitly selected JSON/JSONL transcript.")
    imp.add_argument("--input", required=True, type=Path)
    imp.add_argument("--source", choices=["auto", "codex", "claude", "harness", "generic"], default="auto")
    imp.add_argument("--leaf-id", help="Explicit Claude branch endpoint when history branches.")
    imp.add_argument("--max-record-mib", type=int, default=8,
                     help="Explicit JSONL record read limit, 1–64 MiB (default: 8).")
    imp.add_argument("--output", required=True, type=Path)
    cap = commands.add_parser("capture", help="Capture an identified current session before its invoking user message.")
    cap.add_argument("--input", type=Path)
    cap.add_argument("--source", choices=["auto", "codex", "claude", "harness", "generic"], default="auto")
    cap.add_argument("--session-id")
    cap.add_argument("--session-root", type=Path)
    cap.add_argument("--leaf-id")
    cutoff = cap.add_mutually_exclusive_group(required=True)
    cutoff.add_argument("--before-message-id")
    cutoff.add_argument("--before-text-file", type=Path)
    cap.add_argument("--max-record-mib", type=int, choices=range(1, 65), default=8)
    cap.add_argument("--output", required=True, type=Path)
    prep = commands.add_parser("prepare", help="Freeze evidence and create prompts for the current agent.")
    prep.add_argument("--conversation", required=True, type=Path)
    prep.add_argument("--project", required=True, type=Path)
    prep.add_argument("--docs", nargs="*", default=[], help="Explicit Markdown files/directories relative to project.")
    prep.add_argument("--output", required=True, type=Path)
    prep.add_argument("--allow-partial", action="store_true")
    prep.add_argument("--chunk-chars", type=int, default=24_000)
    check = commands.add_parser("validate", help="Check event provenance against a frozen run.")
    check.add_argument("--run", required=True, type=Path)
    check.add_argument("--events", required=True, type=Path)
    check.add_argument("--output", type=Path)
    report = commands.add_parser("report", help="Validate and render a self-contained, readable HTML review.")
    report.add_argument("--run", required=True, type=Path)
    report.add_argument("--events", required=True, type=Path)
    report.add_argument("--output", required=True, type=Path)
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "capture":
            path = args.input or locate(args.source, args.session_id, args.session_root)
            text = args.before_text_file.read_text(encoding="utf-8") if args.before_text_file else None
            data = capture(path, args.source, args.before_message_id, text, args.leaf_id,
                           args.max_record_mib * 1024 * 1024)
            write_json(args.output, data)
            print(json.dumps({"messages": len(data["messages"]), "selection": data["selection"],
                              "output": str(args.output)}, ensure_ascii=True))
        elif args.command == "import":
            if not 1 <= args.max_record_mib <= 64:
                raise TraceError("--max-record-mib must be between 1 and 64.")
            data = import_conversation(args.input, args.source, args.leaf_id,
                                       args.max_record_mib * 1024 * 1024)
            write_json(args.output, data)
            print(json.dumps({"conversation_id": data["conversation_id"], "messages": len(data["messages"]),
                              "coverage": data["coverage"], "output": str(args.output)}, ensure_ascii=True))
        elif args.command == "prepare":
            data = prepare(args.conversation, args.project, args.docs, args.output,
                           args.allow_partial, args.chunk_chars)
            print(json.dumps({"run_id": data["run_id"], "prompt_count": data["prompt_count"],
                              "next": "Read ANALYZE.md and all prompts; author events.json, then validate/report.",
                              "output": str(args.output)}, ensure_ascii=True))
        elif args.command == "validate":
            data = validate(args.run, read_json(args.events))
            if args.output:
                write_json(args.output, data)
            print(json.dumps(data, ensure_ascii=True, indent=2))
            return 0 if data["valid"] else 1
        elif args.command == "report":
            text, validation = render(args.run, read_json(args.events))
            write_text(args.output, text)
            print(json.dumps({"report": str(args.output), "events": validation["events_checked"],
                              "quotes": validation["quotes_checked"]}, ensure_ascii=True))
        return 0
    except (TraceError, OSError, UnicodeError) as exc:
        print(f"steertrace: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
