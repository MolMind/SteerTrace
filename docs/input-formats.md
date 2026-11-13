# Input formats and coverage

Use explicit files. SteerTrace does not discover all account sessions. The v0.1
importers are conservative readers, not a promise to support every historical
version, remote session, plugin event, or proprietary storage format.

## Generic JSON

A JSON array or `{"messages":[...]}` with `role`, `content`, and optional unique
string `id` and `timestamp`. User and assistant text is retained; tool/system
content is excluded. Text blocks in multimodal arrays are supported; images are
not analyzed. Originality of user-submitted text remains unknown.

```json
[
  {"id":"a1","role":"assistant","content":"We could optimize with per-app rules."},
  {"id":"u1","role":"user","content":"I need a cross-app method instead."}
]
```

An application using DeepSeek or another model can export this format. The model
provider is not the session store. No DeepSeek web export or hidden endpoint is
implemented by this project.

## Codex JSONL

Prefer `response_item` records with a message payload and role-labeled text. IDs
are `r<logical-record-number>`. Do not also count duplicate event_msg dialogue.
When response items are unavailable, event_msg user_message/agent_message is a
disclosed fallback. Reasoning and tool bodies are excluded.

Recognized environment/instruction injections are excluded. Recognized question
reply wrappers retain answer text. Authorship filtering is heuristic: user role
does not prove human originality. Compaction is disclosed; rollback histories are
rejected until the caller supplies a selected-branch export.

## Claude Code JSONL

Supports simple user/assistant nodes with uuid, parentUuid and message.content.
When multiple leaves exist, supply `--leaf-id <uuid>`; only that parent chain is
retained. Cycles, duplicate UUIDs and missing parents are rejected. Some real
transcripts use additional topology records or compaction formats; unsupported
chains should be exported to generic selected-branch JSON rather than silently
mixed or interpreted as complete. Subagent logs are not merged automatically.

## Limits

- Input file limit: 128 MiB; JSONL logical record limit: 8 MiB by default. When an
  identified record exceeds that default, explicitly use `import --max-record-mib
  64` (maximum 64 MiB) and re-import to a new file rather than hiding partial input.
- Malformed/oversized JSONL records are skipped with incomplete coverage; prepare
  refuses this input unless `--allow-partial` is explicit.
- Source completeness always remains unknown. A successful full file read does
  not prove that earlier history was never deleted or compressed.
- Documents: explicit Markdown paths/directories within project; at most 64 files,
  512 KiB per file and 300,000 total characters. Outside-root symlinks are rejected.
- Text credential redaction is best-effort. Business information and paths may
  remain. Review selected inputs and output before publishing or sending to an agent.
- Plain-text `/export` renderings and Agent Insight report.json are not accepted
  as full source conversations by a dedicated adapter. Convert to explicit
  role-labeled JSON with preserved provenance; do not invent missing turns.
