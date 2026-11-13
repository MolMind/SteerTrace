"""Replay the public hand-authored example; never claim autonomous analysis."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from steertrace.importer import import_conversation
from steertrace.pipeline import prepare
from steertrace.report import render
from steertrace.storage import read_json, write_json, write_text


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "demo"
    # prepare refuses overwrite before creating any demo analysis.
    source = ROOT / "examples" / "synthetic"
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        normalized = Path(temporary) / "conversation.json"
        write_json(normalized, import_conversation(source / "conversation.json"))
        manifest = prepare(normalized, ROOT, ["examples/synthetic/plan.md"], output)
    analysis = read_json(source / "analysis.json")
    analysis["run_id"] = manifest["run_id"]
    write_json(output / "events.json", analysis)
    text, validation = render(output, analysis)
    write_json(output / "validation.json", validation)
    write_text(output / "report.html", text)
    print("Synthetic, hand-authored replay; not an autonomous model evaluation.")
    print(output.resolve() / "report.html")


if __name__ == "__main__":
    main()
