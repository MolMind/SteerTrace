import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from steertrace.importer import import_conversation
from steertrace.pipeline import prepare
from steertrace.report import render
from steertrace.storage import TraceError, read_json, write_json
from steertrace.validation import validate

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.conversation = self.root / "conversation.json"
        write_json(self.conversation, import_conversation(ROOT / "examples/synthetic/conversation.json"))
        self.run = self.root / "run"
        self.manifest = prepare(self.conversation, ROOT, ["examples/synthetic/plan.md"], self.run)
        self.events = read_json(ROOT / "examples/synthetic/analysis.json")
        self.events["run_id"] = self.manifest["run_id"]

    def assert_invalid(self, analysis, text):
        result = validate(self.run, analysis)
        self.assertFalse(result["valid"], result)
        self.assertTrue(any(text in e for e in result["errors"]), result)

    def test_example_end_to_end(self):
        text, checked = render(self.run, self.events)
        self.assertTrue(checked["valid"])
        self.assertEqual(checked["events_checked"], 5)
        self.assertIn("你同意继续", text)
        self.assertIn("实验还没有执行", text)
        self.assertIn("按对话先后排列", text)

    def test_fabricated_user_quote_is_rejected(self):
        self.events["events"][0]["user_evidence"][0]["quote"] = "The user never said this."
        self.assert_invalid(self.events, "quotation does not match")
        with self.assertRaisesRegex(TraceError, "Report refused"):
            render(self.run, self.events)

    def test_assistant_text_cannot_be_user_evidence(self):
        self.events["events"][0]["user_evidence"] = [{"message_id": "a1", "quote": "可以先补全"}]
        self.assert_invalid(self.events, "not a user")

    def test_unknown_origin_not_eligible(self):
        c = read_json(self.conversation)
        c["messages"][1]["origin"] = "unknown"
        other = self.root / "other.json"
        write_json(other, c)
        run = self.root / "other"
        manifest = prepare(other, ROOT, ["examples/synthetic/plan.md"], run)
        self.events["run_id"] = manifest["run_id"]
        result = validate(run, self.events)
        self.assertTrue(any("human-submitted" in x for x in result["errors"]))

    def test_wrong_temporal_order_is_rejected(self):
        self.events["events"][0]["before"] = [{"message_id": "a5", "quote": "下一步准备测试"}]
        self.assert_invalid(self.events, "not before")

    def test_acknowledgment_is_not_invention(self):
        self.events["events"][3]["ownership"] = "human_proposed"
        self.assert_invalid(self.events, "acknowledgment")

    def test_ai_selection_requires_proposal_evidence(self):
        self.events["events"][2]["before"] = []
        self.assert_invalid(self.events, "requires before")

    def test_document_quote_must_match_snapshot(self):
        self.events["events"][0]["document_links"][0]["quote"] = "all experiments passed"
        self.assert_invalid(self.events, "document quote")

    def test_report_does_not_claim_independent_verification(self):
        self.events["events"][0]["document_links"][0]["verification"] = "independently_verified"
        self.assert_invalid(self.events, "independent reproduction")

    def test_recommendation_effect_is_hypothetical(self):
        self.events["recommendations"][0]["status"] = "proven"
        self.assert_invalid(self.events, "hypothesis")

    def test_unknown_event_reference_is_rejected(self):
        self.events["recommendations"][0]["event_ids"] = ["missing"]
        self.assert_invalid(self.events, "existing event")

    def test_duplicate_events_are_rejected(self):
        event = copy.deepcopy(self.events["events"][0])
        event["id"] = "E5"
        self.events["events"].append(event)
        self.assert_invalid(self.events, "duplicate event content")

    def test_wrong_run_is_rejected(self):
        self.events["run_id"] = "wrong"
        self.assert_invalid(self.events, "run_id")

    def test_tampered_snapshot_is_rejected(self):
        path = self.run / "conversation.json"
        c = read_json(path)
        c["messages"][0]["text"] += "tampered"
        path.write_text(json.dumps(c))
        with self.assertRaisesRegex(TraceError, "hash mismatch"):
            validate(self.run, self.events)

    def test_empty_analysis_is_valid_without_forcing_findings(self):
        self.events["events"] = []
        self.events["criticisms"] = []
        self.events["recommendations"] = []
        text, checked = render(self.run, self.events)
        self.assertTrue(checked["valid"])
        self.assertIn("没有记录可支持", text)

    def test_malformed_model_fields_return_errors_not_traceback(self):
        for field in ["kind", "ownership", "evidence_posture"]:
            events = copy.deepcopy(self.events)
            events["events"][0][field] = []
            self.assert_invalid(events, "unsupported")

    def test_partial_input_requires_explicit_opt_in(self):
        c = read_json(self.conversation)
        c["coverage"]["parser_complete"] = False
        p = self.root / "partial.json"
        write_json(p, c)
        with self.assertRaisesRegex(TraceError, "incomplete"):
            prepare(p, ROOT, [], self.root / "partial-run")

    def test_outside_document_is_rejected(self):
        with self.assertRaisesRegex(TraceError, "escapes"):
            prepare(self.conversation, ROOT, [str(self.conversation)], self.root / "outside")

    def test_symlink_escape_is_rejected(self):
        project = self.root / "project"
        project.mkdir()
        (project / "escape.md").symlink_to(self.conversation)
        with self.assertRaisesRegex(TraceError, "escapes"):
            prepare(self.conversation, project, ["escape.md"], self.root / "symlink")

    def test_no_implicit_document_scan(self):
        manifest = prepare(self.conversation, ROOT, [], self.root / "nodocs")
        self.assertEqual(manifest["document_count"], 0)

    def test_document_credentials_are_not_exposed_to_prompts(self):
        project = self.root / "private-project"
        project.mkdir()
        (project / "plan.md").write_text("api_key: sk-abcdefghijklmnopqrstuv\nUseful plan.")
        out = self.root / "private-run"
        prepare(self.conversation, project, ["plan.md"], out)
        text = (out / "documents.json").read_text()
        self.assertNotIn("sk-abcdefghijklmnopqrstuv", text)
        self.assertIn("REDACTED", text)

    def test_acknowledgment_with_malformed_ownership_returns_error(self):
        self.events["events"][3]["ownership"] = []
        self.assert_invalid(self.events, "unsupported")

    def test_no_overwrite(self):
        with self.assertRaisesRegex(TraceError, "exists"):
            prepare(self.conversation, ROOT, [], self.run)

    def test_long_message_tail_is_preserved_across_packets(self):
        c = read_json(self.conversation)
        c["messages"][0]["text"] = "x" * 4000 + "IMPORTANT_FINAL_CONSTRAINT"
        p = self.root / "long.json"
        write_json(p, c)
        out = self.root / "long-run"
        manifest = prepare(p, ROOT, [], out, max_chars=1000)
        packets = sorted((out / "prompts").glob("*.md"))
        self.assertGreater(manifest["prompt_count"], 1)
        self.assertTrue(any("IMPORTANT_FINAL_CONSTRAINT" in p.read_text() for p in packets))

    def test_criticism_requires_an_existing_event(self):
        self.events["criticisms"][0]["event_ids"] = ["invented"]
        self.assert_invalid(self.events, "Criticism must cite existing")

    def test_criticism_requires_actionable_fields_and_basis(self):
        for field in ("problem", "consequence", "better_move", "title"):
            analysis = copy.deepcopy(self.events)
            analysis["criticisms"][0][field] = ""
            self.assert_invalid(analysis, "criticism: " + field)
        self.events["criticisms"][0]["basis"] = "certain_personality_trait"
        self.assert_invalid(self.events, "Criticism basis")

    def test_malformed_review_is_rejected(self):
        for value in (None, [], {"headline": "Title", "summary": "Summary", "keep_doing": [None]}):
            analysis = copy.deepcopy(self.events)
            analysis["review"] = value
            self.assert_invalid(analysis, "review")

    def test_old_analysis_gets_no_manufactured_criticism(self):
        del self.events["review"]
        del self.events["criticisms"]
        text, checked = render(self.run, self.events)
        self.assertTrue(checked["valid"])
        self.assertIn("未呈现有充分依据的判断偏差", text)

    def test_inferred_criticism_is_labeled(self):
        self.events["criticisms"][0]["basis"] = "inference"
        text, _ = render(self.run, self.events)
        self.assertIn("这是基于上下文的推测，需要你核对", text)

    def test_html_escapes_model_text(self):
        attack = '<script src="https://evil.invalid/x"></script><img src=x onerror=alert(1)>'
        self.events["review"]["headline"] = attack
        self.events["criticisms"][0]["problem"] = attack
        self.events["events"][0]["summary"] = attack
        self.events["recommendations"][0]["text"] = attack
        self.events["limitations"].append(attack)
        text, _ = render(self.run, self.events)
        self.assertNotIn(attack, text)
        self.assertIn("&lt;script", text)
        self.assertEqual(text.count("<script>"), 1)

    def test_html_is_offline_and_hides_internal_labels(self):
        from html.parser import HTMLParser
        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.external = []
                self.icons = []
            def handle_starttag(self, tag, attrs):
                if tag == "svg":
                    self.icons.append(dict(attrs))
                for key, value in attrs:
                    if key in {"src", "href"} and value and not value.startswith("#"):
                        self.external.append(value)
        text, _ = render(self.run, self.events)
        parser = Parser()
        parser.feed(text)
        self.assertFalse(parser.external)
        self.assertTrue(parser.icons)
        for attributes in parser.icons:
            self.assertIn("icon-tabler", attributes.get("class", "").split())
            self.assertEqual(attributes.get("aria-hidden"), "true")
        self.assertTrue(text.startswith("<!doctype html>"))
        for label in ("authorization_only", "observed_submission", self.manifest["run_id"], "消息 `u1`"):
            self.assertNotIn(label, text)
        self.assertIn(self.events["criticisms"][0]["title"], text)

    def test_cli_report_outputs_html(self):
        path = self.root / "events.json"
        write_json(path, self.events)
        output = self.root / "report.html"
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run([sys.executable, "-m", "steertrace", "report", "--run", str(self.run),
                               "--events", str(path), "--output", str(output)], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(output.read_text().startswith("<!doctype html>"))

    def test_cli_validation_failure_has_nonzero_status(self):
        self.events["events"][0]["user_evidence"][0]["quote"] = "invented"
        p = self.root / "events.json"
        write_json(p, self.events)
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run([sys.executable, "-m", "steertrace", "validate", "--run", str(self.run), "--events", str(p)], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
