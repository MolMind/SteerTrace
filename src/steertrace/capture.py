"""Resolve an identified session and freeze dialogue before the invoking message."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from .importer import import_conversation, redact, user_content
from .storage import TraceError


def locate(client: str, session_id: str | None, root: Path | None = None) -> Path:
    if client == 'codex':
        session_id = session_id or os.environ.get('CODEX_THREAD_ID')
        root = root or Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'sessions'
    elif client == 'claude':
        root = root or Path.home() / '.claude' / 'projects'
    else:
        raise TraceError('This client requires a native transcript/export path via --input.')
    if not session_id or not re.fullmatch(r'[A-Za-z0-9_-]+', session_id):
        raise TraceError('A reliable current session ID is required; never select the latest file.')
    # Match names only; do not open unrelated session histories.
    matches = list(root.rglob(f'*{session_id}.jsonl'))
    matches = [p for p in matches if p.stem == session_id or p.stem.endswith('-' + session_id)]
    if len(matches) != 1:
        raise TraceError('Session path is missing or ambiguous; use the native transcript path.')
    return matches[0]


def capture(path: Path, source: str, before_id: str | None = None,
            before_text: str | None = None, leaf_id: str | None = None,
            max_record_bytes: int | None = None) -> dict:
    if (before_id is None) == (before_text is None):
        raise TraceError('Provide exactly one cutoff: invoking user message ID or exact full text.')
    data = import_conversation(path, source, leaf_id, max_record_bytes)
    if before_text is not None:
        before_text = redact(user_content(before_text)[0])
        if not before_text:
            raise TraceError('Invoking message text must not be empty.')
    matches = [i for i, m in enumerate(data['messages']) if m['role'] == 'user' and
               (m['id'] == before_id if before_id is not None else m['text'] == before_text)]
    if len(matches) != 1:
        raise TraceError('Invoking user message missing or ambiguous; supply its exact ID. No capture written.')
    index = matches[0]
    if index == 0:
        raise TraceError('No dialogue precedes the invoking message.')
    boundary = data['messages'][index]['id']
    data['messages'] = data['messages'][:index]
    data['selection'] = {'mode': 'before_invocation', 'excluded_from_message_id': boundary}
    data['conversation_id'] = hashlib.sha256((data['source_sha256'] + ':' + boundary).encode()).hexdigest()[:16]
    return data
