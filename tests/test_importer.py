import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from steertrace.importer import import_conversation, load_records, redact
from steertrace.storage import TraceError


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def records(self, rows, suffix=".jsonl"):
        path = self.root / ("input" + suffix)
        text = "\n".join(json.dumps(x) for x in rows) + "\n" if suffix == ".jsonl" else json.dumps(rows)
        path.write_text(text)
        return path

    def test_codex_prefers_response_messages_without_duplicate_events(self):
        p = self.records([
            {"type": "event_msg", "payload": {"type": "user_message", "message": "hello"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}},
            {"type": "response_item", "payload": {"type": "reasoning", "text": "hidden"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "secret tool body"}},
        ])
        c = import_conversation(p)
        self.assertEqual([x["text"] for x in c["messages"]], ["hello"])
        self.assertEqual(c["messages"][0]["id"], "r2")

    def test_codex_fallback_discloses_limit(self):
        p = self.records([{"type": "event_msg", "payload": {"type": "user_message", "message": "hello"}}])
        c = import_conversation(p)
        self.assertIn("fallback", c["coverage"]["warnings"][0])

    def test_developer_and_internal_analysis_are_excluded(self):
        p = self.records([
            {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": "host instructions"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "channel": "analysis", "content": "private reasoning"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "Review this"}},
        ])
        c = import_conversation(p)
        self.assertEqual([m["text"] for m in c["messages"]], ["Review this"])
        self.assertTrue(c["coverage"]["parser_complete"])

    def test_explicit_record_limit_recovers_full_read(self):
        p = self.records([{"role": "user", "content": "x" * 200}])
        self.assertTrue(import_conversation(p, "generic", max_record_bytes=1000)["coverage"]["parser_complete"])

    def test_invalid_record_type_fails_cleanly(self):
        p = self.records([{"type": [], "role": "user", "content": "hello"}])
        with self.assertRaisesRegex(TraceError, "Record type"):
            import_conversation(p)

    def test_source_change_during_import_is_rejected(self):
        p = self.records([{"role": "user", "content": "original"}], ".json")
        def changing_reader(path, limit):
            result = load_records(path, limit)
            path.write_text('[{"role":"user","content":"changed"}]')
            return result
        with patch("steertrace.importer.load_records", side_effect=changing_reader):
            with self.assertRaisesRegex(TraceError, "changed during import"):
                import_conversation(p)

    def test_machine_instructions_are_not_user_evidence(self):
        p = self.records([{"role": "user", "content": "# AGENTS.md instructions\nbe brave"},
                          {"role": "user", "content": "Check the decision"}], ".json")
        c = import_conversation(p)
        self.assertEqual(len(c["messages"]), 1)
        self.assertEqual(c["coverage"]["excluded_non_dialogue"], 1)

    def test_question_reply_preserves_answer_not_machine_question(self):
        wrapper = '<send_user_message_question_reply>\n[{"question":"secret question", "answer":"Use local files"}]\n</send_user_message_question_reply>'
        p = self.records([{"role": "user", "content": wrapper}], ".json")
        self.assertEqual(import_conversation(p)["messages"][0]["text"], "Use local files")

    def test_unknown_wrapper_is_not_assumed_human(self):
        p = self.records([{"role": "user", "content": "<send_user_message_question_reply>broken"}], ".json")
        self.assertEqual(import_conversation(p)["messages"][0]["origin"], "unknown")

    def test_redaction_includes_private_key_and_tokens(self):
        text = "sk-abcdefghijklmnopqrstuv\nAuthorization: Bearer abcdefghijklmnopqrstuv\nkey：12345678-1234-1234-1234-123456789012\n-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----"
        cleaned = redact(text)
        for secret in ["sk-abcdef", "Bearer abc", "12345678-1234", "\nabc\n"]:
            self.assertNotIn(secret, cleaned)
        self.assertIn("REDACTED_PRIVATE_KEY", cleaned)

    def test_generic_multimodal_text_without_image_data(self):
        p = self.records([{"role": "user", "content": [{"type": "text", "text": "Look here"}, {"type": "image_url", "image_url": "data:secret"}]}], ".json")
        self.assertEqual(import_conversation(p)["messages"][0]["text"], "Look here")

    def test_duplicate_ids_fail(self):
        p = self.records([{"id": "x", "role": "user", "content": "a"}, {"id": "x", "role": "assistant", "content": "b"}], ".json")
        with self.assertRaises(TraceError):
            import_conversation(p)

    def test_malformed_record_marks_partial(self):
        p = self.records([{"role": "user", "content": "a"}])
        with p.open("a") as stream:
            stream.write("not json\n")
        c = import_conversation(p)
        self.assertFalse(c["coverage"]["parser_complete"])

    def test_oversized_record_is_bounded_and_disclosed(self):
        p = self.records([{"role": "user", "content": "x" * 200}, {"role": "user", "content": "ok"}])
        with patch("steertrace.importer.MAX_RECORD_BYTES", 100):
            c = import_conversation(p, "generic")
        self.assertFalse(c["coverage"]["parser_complete"])
        self.assertEqual(c["messages"][0]["text"], "ok")

    def test_bad_codex_payload_is_not_silent_success(self):
        p = self.records([{"type": "response_item", "payload": []},
                          {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "ok"}}])
        self.assertFalse(import_conversation(p)["coverage"]["parser_complete"])

    def test_rollback_requires_branch_export(self):
        p = self.records([{"type": "event_msg", "payload": {"type": "thread_rolled_back"}}])
        with self.assertRaisesRegex(TraceError, "rollback"):
            import_conversation(p)

    def test_compaction_does_not_claim_original_completeness(self):
        p = self.records([{"type": "compacted"}, {"type": "event_msg", "payload": {"type": "user_message", "message": "hello"}}])
        c = import_conversation(p)
        self.assertEqual(c["coverage"]["source_completeness"], "unknown")
        self.assertTrue(any("Compaction" in x for x in c["coverage"]["warnings"]))

    def test_claude_forks_are_not_merged(self):
        p = self.records([
            {"uuid": "u", "type": "user", "parentUuid": None, "message": {"content": "choose"}},
            {"uuid": "a", "type": "assistant", "parentUuid": "u", "message": {"content": "A"}},
            {"uuid": "b", "type": "assistant", "parentUuid": "u", "message": {"content": "B"}},
        ])
        with self.assertRaisesRegex(TraceError, "multiple branches"):
            import_conversation(p)
        self.assertEqual([m["id"] for m in import_conversation(p, leaf_id="b")["messages"]], ["u", "b"])

    def test_claude_orphan_is_rejected(self):
        p = self.records([{"uuid": "a", "type": "assistant", "parentUuid": "missing", "message": {"content": "A"}}])
        with self.assertRaisesRegex(TraceError, "Missing Claude parent"):
            import_conversation(p)


if __name__ == "__main__":
    unittest.main()
