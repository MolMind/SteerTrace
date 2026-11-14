"""Explicit-file importers. Never discover account-wide histories."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .storage import TraceError

CONVERSATION_SCHEMA = "steertrace.conversation/v1"
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_RECORD_BYTES = 8 * 1024 * 1024
ROLES = {"user", "assistant", "system", "developer", "tool"}


def redact(text: str) -> str:
    """Best-effort credential redaction, not a privacy certification."""
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
                  "[REDACTED_PRIVATE_KEY]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}", "[REDACTED_TOKEN]", text)
    text = re.sub(r"(?i)(\bBearer\s+)[A-Za-z0-9_.~+/-]{16,}", r"\1[REDACTED_TOKEN]", text)
    return re.sub(r"(?im)((?:api[_ -]?key|access[_ -]?token|password|密码|密钥|\bkey)"
                  r"\s*[：:=]\s*)[^\s\"'`,;]{12,}", r"\1[REDACTED_SECRET]", text)


def text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content
                         if isinstance(part, dict) and part.get("type") in
                         {"text", "input_text", "output_text"}
                         and isinstance(part.get("text"), str))
    return ""


def user_content(text: str) -> tuple[str, str]:
    """Recognize common machine envelopes without asserting human originality."""
    stripped = text.strip()
    if stripped.startswith(("<environment_context>", "# AGENTS.md instructions",
                            "<permissions instructions>", "<turn_aborted>")):
        return "", "system_injected"
    if stripped.startswith("<send_user_message_question_reply>"):
        try:
            body = stripped.split(">", 1)[1].rsplit("</", 1)[0]
            replies = json.loads(body)
            answers = [x["answer"] for x in replies
                       if isinstance(x, dict) and isinstance(x.get("answer"), str)]
            return "\n".join(answers), "human_submitted"
        except (ValueError, TypeError, KeyError):
            return text, "unknown"
    if stripped.startswith("# Files mentioned by the user:") and "## My request:" in text:
        text = text.split("## My request:", 1)[1]
        text = re.sub(r"<image\b[\s\S]*?</image>", "[image attachment]", text)
    return text.strip(), "human_submitted"


def load_records(path: Path, max_record_bytes: int | None = None) -> tuple[list[dict], list[str], bool]:
    max_record_bytes = MAX_RECORD_BYTES if max_record_bytes is None else max_record_bytes
    if not isinstance(max_record_bytes, int) or not 1 <= max_record_bytes <= 64 * 1024 * 1024:
        raise TraceError("Record byte limit must be positive and at most 64 MiB.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise TraceError("Input exceeds 128 MiB; explicitly select a smaller export.")
    warnings: list[str] = []
    partial = False
    if path.suffix.lower() != ".jsonl":
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise TraceError(f"Invalid JSON: {exc}") from exc
        records = obj.get("messages") if isinstance(obj, dict) else obj
        if not isinstance(records, list):
            raise TraceError("JSON must be a messages array or an object containing messages.")
        if not all(isinstance(x, dict) for x in records):
            raise TraceError("Every message must be an object.")
        return records, warnings, partial
    records = []
    # Bounded reads: discard oversized logical records, report incomplete input.
    with path.open("rb") as stream:
        number = 0
        while True:
            line = stream.readline(max_record_bytes + 1)
            if not line:
                break
            number += 1
            if len(line) > max_record_bytes:
                while line and not line.endswith(b"\n"):
                    line = stream.readline(max_record_bytes + 1)
                warnings.append(f"Oversized JSONL record at logical line {number} omitted.")
                partial = True
                continue
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("record is not an object")
                records.append(record)
            except (ValueError, UnicodeError):
                warnings.append(f"Malformed JSONL record at logical line {number} omitted.")
                partial = True
    return records, warnings, partial


def claude_branch(records: list[dict], leaf_id: str | None) -> list[dict]:
    if any(r.get("parentUuid") is not None and not isinstance(r.get("parentUuid"), str)
           for r in records if r.get("type") in {"user", "assistant"}):
        raise TraceError("Claude parent UUID must be a string or null.")
    nodes = {r["uuid"]: r for r in records if isinstance(r.get("uuid"), str)
             and r.get("type") in {"user", "assistant"}}
    if not nodes:
        raise TraceError("No Claude user/assistant message chain found.")
    if len(nodes) != sum(r.get("type") in {"user", "assistant"}
                         and isinstance(r.get("uuid"), str) for r in records):
        raise TraceError("Duplicate Claude message UUIDs; choose an unambiguous export.")
    parents = {r.get("parentUuid") for r in nodes.values()}
    leaves = sorted(set(nodes) - parents)
    if leaf_id is None:
        if len(leaves) != 1:
            raise TraceError("Claude transcript has multiple branches; supply --leaf-id: "
                             + ", ".join(leaves))
        leaf_id = leaves[0]
    if leaf_id not in nodes:
        raise TraceError("Selected Claude leaf ID does not exist.")
    chain, seen = [], set()
    current = leaf_id
    while current:
        if current in seen:
            raise TraceError("Cycle in Claude parent chain.")
        if current not in nodes:
            raise TraceError("Missing Claude parent; export a complete selected branch.")
        seen.add(current)
        node = nodes[current]
        chain.append(node)
        current = node.get("parentUuid")
    return list(reversed(chain))


def import_conversation(path: Path, source: str = "auto", leaf_id: str | None = None,
                        max_record_bytes: int | None = None) -> dict:
    path = path.resolve()
    if path.stat().st_size > MAX_FILE_BYTES:
        raise TraceError("Input exceeds 128 MiB; explicitly select a smaller export.")
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    records, warnings, partial = load_records(path, max_record_bytes)
    if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha:
        raise TraceError("Source changed during import; select a stable export and retry.")
    for row in records:
        if "type" in row and not isinstance(row["type"], str):
            raise TraceError("Record type must be a string when present.")
    if source == "auto":
        if any(r.get("type") in {"session_meta", "response_item", "event_msg"} for r in records):
            source = "codex"
        elif any("uuid" in r and r.get("type") in {"user", "assistant"} for r in records):
            source = "claude"
        elif any(r.get("type") in {"user/message", "assistant/message"} for r in records):
            source = "harness"
        else:
            source = "generic"
    if source not in {"codex", "claude", "harness", "generic"}:
        raise TraceError(f"Unsupported source: {source}")
    if leaf_id and source != "claude":
        raise TraceError("--leaf-id applies only to Claude.")
    candidates = []
    if source == "claude":
        for row in claude_branch(records, leaf_id):
            msg = row.get("message", {})
            candidates.append((row["uuid"], row.get("type"), msg.get("content"), row.get("timestamp")))
    elif source == "harness":
        for i, row in enumerate(records, 1):
            if row.get("type") not in {"user/message", "assistant/message"}:
                continue
            if row.get("surfaceOp") != "append":
                raise TraceError("Harness non-append history requires a native selected-branch export.")
            payload = row.get("data", {})
            if not isinstance(payload, dict):
                raise TraceError("Invalid Harness message data.")
            msg = payload.get("message", {}) if row["type"] == "assistant/message" else payload
            if not isinstance(msg, dict) or not isinstance(msg.get("id"), str):
                raise TraceError("Harness message requires a stable ID.")
            if row["type"] == "user/message" and (not isinstance(msg.get("source"), dict) or msg["source"].get("kind") != "user"):
                excluded_role = "tool"
            else:
                excluded_role = "user" if row["type"] == "user/message" else "assistant"
            candidates.append((msg["id"], excluded_role, msg.get("content"), row.get("time")))
    elif source == "codex":
        rollback_types = ("thread_rolled_back", "conversation_rollback", "thread_rollback")
        if any(r.get("type") in rollback_types or
               (isinstance(r.get("payload"), dict) and r["payload"].get("type") in rollback_types)
               for r in records):
            raise TraceError("Codex rollback detected; export the selected branch before importing.")
        if any(r.get("type") in {"compacted", "context_compacted"} for r in records):
            warnings.append("Compaction marker present; retained text is not proof of full original history.")
        for i, row in enumerate(records, 1):
            payload = row.get("payload", {})
            if not isinstance(payload, dict):
                warnings.append(f"Invalid Codex payload at record {i}; omitted.")
                partial = True
                continue
            if row.get("type") == "response_item" and payload.get("type") == "message":
                if payload.get("channel") in ("analysis", "summary"):
                    continue
                candidates.append((f"r{i}", payload.get("role"), payload.get("content"), row.get("timestamp")))
        if not candidates:
            warnings.append("Using Codex event_msg fallback; response_item dialogue was unavailable.")
            for i, row in enumerate(records, 1):
                payload = row.get("payload", {})
                if not isinstance(payload, dict):
                    continue
                kind = payload.get("type")
                if not isinstance(kind, str):
                    continue
                role = {"user_message": "user", "agent_message": "assistant"}.get(kind)
                if row.get("type") == "event_msg" and role:
                    candidates.append((f"r{i}", role, payload.get("message"), row.get("timestamp")))
    else:
        for i, row in enumerate(records, 1):
            candidates.append((str(row.get("id", f"m{i}")), row.get("role"), row.get("content"), row.get("timestamp")))
    messages, ids = [], set()
    excluded = 0
    for mid, role, content, timestamp in candidates:
        if not isinstance(role, str) or role not in ROLES:
            warnings.append(f"Unknown role at message {mid}; omitted.")
            partial = True
            continue
        if role not in {"user", "assistant"}:
            excluded += 1
            continue
        text = text_content(content)
        origin = "assistant_generated"
        if role == "user":
            text, origin = user_content(text)
        if not text.strip():
            excluded += 1
            continue
        if not mid.strip():
            raise TraceError("Message IDs must not be empty.")
        if mid in ids:
            raise TraceError(f"Duplicate message ID: {mid}")
        ids.add(mid)
        cleaned = redact(text)
        messages.append({"id": mid, "role": role, "origin": origin, "text": cleaned,
                         "timestamp": timestamp, "redacted": cleaned != text})
    if not messages:
        raise TraceError("No readable dialogue messages in selected input.")
    return {"schema_version": CONVERSATION_SCHEMA, "conversation_id": source_sha[:16],
            "source": source, "source_sha256": source_sha, "selected_leaf_id": leaf_id,
            "messages": messages, "coverage": {"parser_complete": not partial,
            "source_completeness": "unknown", "excluded_non_dialogue": excluded,
            "warnings": warnings, "authorship": "Submission origin is not proof of human originality."}}
