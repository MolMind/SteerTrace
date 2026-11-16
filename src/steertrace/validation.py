"""Check provenance and structural invariants, not the truth of interpretations."""
from __future__ import annotations

from pathlib import Path

from .pipeline import EVENT_SCHEMA, check_conversation
from .storage import TraceError, digest, read_json

KINDS = {"goal", "question", "critique", "constraint", "tradeoff", "selection", "authorization", "stop"}
OWNERSHIP = {"human_proposed", "ai_proposed_human_selected", "authorization_only", "unknown"}
POSTURES = {"observed_submission", "contextual_inference", "unknown"}
RELATIONS = {"records_matching_constraint", "records_plan", "reports_result"}
VERIFICATION = {"documented", "reported_result", "unknown"}
FILLER = {"继续", "可以", "好的", "好", "ok", "yes", "continue"}


def load_run(run: Path) -> tuple[dict, dict, list[dict]]:
    manifest = read_json(run / "manifest.json")
    conversation = read_json(run / "conversation.json")
    documents = read_json(run / "documents.json")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "steertrace.run/v1":
        raise TraceError("Unsupported run manifest.")
    check_conversation(conversation)
    if not isinstance(documents, list) or any(not isinstance(x, dict) for x in documents):
        raise TraceError("Invalid document snapshot.")
    if digest(conversation) != manifest.get("conversation_sha256"):
        raise TraceError("Conversation snapshot hash mismatch.")
    if digest(documents) != manifest.get("documents_sha256"):
        raise TraceError("Document snapshot hash mismatch.")
    return manifest, conversation, documents


def validate(run: Path, events: dict) -> dict:
    manifest, conversation, documents = load_run(run)
    errors, warnings = [], []
    messages = {m["id"]: m for m in conversation["messages"]}
    order = {m["id"]: i for i, m in enumerate(conversation["messages"])}
    docs = {d["id"]: d for d in documents}
    checked_quotes = 0

    def error(message: str) -> None:
        errors.append(message)

    def required_text(obj: dict, field: str, label: str) -> None:
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            error(f"{label}: {field} must be non-empty text.")

    def references(refs: object, role: str, label: str, required: bool = False) -> list[int]:
        nonlocal checked_quotes
        if not isinstance(refs, list) or (required and not refs):
            error(f"{label}: expected {'non-empty ' if required else ''}reference array.")
            return []
        positions = []
        for ref in refs:
            if not isinstance(ref, dict):
                error(f"{label}: reference must be an object.")
                continue
            mid, quote = ref.get("message_id"), ref.get("quote")
            if not isinstance(mid, str) or mid not in messages:
                error(f"{label}: unknown message ID {mid!r}.")
                continue
            message = messages[mid]
            if message["role"] != role:
                error(f"{label}: {mid} is not a {role} message.")
            if role == "user" and message.get("origin") != "human_submitted":
                error(f"{label}: {mid} lacks eligible human-submitted provenance.")
            if not isinstance(quote, str) or not quote.strip() or quote not in message["text"]:
                error(f"{label}: quotation does not match {mid} exactly.")
            elif "[REDACTED_" in quote:
                error(f"{label}: credential placeholders cannot support a judgment event.")
            else:
                checked_quotes += 1
                if role == "assistant" and len(quote.strip()) < 12 and len(message["text"]) > 40:
                    warnings.append(f"{label}: short AI excerpt in {mid}; review semantic completeness manually.")
            positions.append(order[mid])
        return positions

    if not isinstance(events, dict):
        return {"valid": False, "errors": ["Analysis must be an object."], "warnings": []}
    if events.get("schema_version") != EVENT_SCHEMA:
        error("Unsupported event schema.")
    if events.get("run_id") != manifest["run_id"]:
        error("Analysis run_id does not match frozen evidence.")
    items = events.get("events")
    if not isinstance(items, list):
        error("events must be an array.")
        items = []
    ids, fingerprints = set(), set()
    for n, event in enumerate(items, 1):
        label = f"event {n}"
        if not isinstance(event, dict):
            error(f"{label}: must be an object.")
            continue
        eid = event.get("id")
        if not isinstance(eid, str) or not eid.strip():
            error(f"{label}: missing ID.")
        elif eid in ids:
            error(f"{label}: duplicate ID {eid}.")
        else:
            ids.add(eid)
        for field in ("summary", "interpretation", "uncertainty"):
            required_text(event, field, label)
        for field, allowed in (("kind", KINDS), ("ownership", OWNERSHIP), ("evidence_posture", POSTURES)):
            if not isinstance(event.get(field), str) or event[field] not in allowed:
                error(f"{label}: unsupported {field}.")
        if "ai_response" in event:
            required_text(event, "ai_response", label)
            if not event.get("after"):
                error(f"{label}: ai_response requires after evidence.")
        else:
            warnings.append(f"{eid or label}: legacy event has no ai_response summary.")
        user = references(event.get("user_evidence"), "user", label + " user", required=True)
        before = references(event.get("before", []), "assistant", label + " before")
        after = references(event.get("after", []), "assistant", label + " after")
        if user and before and max(before) >= min(user):
            error(f"{label}: before evidence is not before the user event.")
        if user and after and min(after) <= max(user):
            error(f"{label}: after evidence is not after the user event.")
        if event.get("ownership") == "ai_proposed_human_selected" and not before:
            error(f"{label}: AI proposal ownership requires before evidence.")
        if user and all(conversation["messages"][i]["text"].strip().lower().rstrip("。.!！")
                        in FILLER for i in user):
            if event.get("ownership") not in ("authorization_only", "unknown"):
                error(f"{label}: acknowledgment alone cannot establish proposal ownership.")
        links = event.get("document_links", [])
        if not isinstance(links, list):
            error(f"{label}: document_links must be an array.")
            links = []
        for link in links:
            if not isinstance(link, dict):
                error(f"{label}: document link must be an object.")
                continue
            did, quote = link.get("doc_id"), link.get("quote")
            if not isinstance(did, str) or did not in docs:
                error(f"{label}: unknown document ID {did!r}.")
            elif not isinstance(quote, str) or not quote.strip() or quote not in docs[did]["text"]:
                error(f"{label}: document quote does not match snapshot.")
            elif "[REDACTED_" in quote:
                error(f"{label}: credential placeholders cannot support a document association.")
            else:
                checked_quotes += 1
            if not isinstance(link.get("relation"), str) or link["relation"] not in RELATIONS:
                error(f"{label}: unsupported document relation.")
            if not isinstance(link.get("verification"), str) or link["verification"] not in VERIFICATION:
                error(f"{label}: verification cannot claim independent reproduction.")
        fingerprint = digest({"kind": event.get("kind"), "summary": event.get("summary"),
                              "user_evidence": event.get("user_evidence")})
        if fingerprint in fingerprints:
            error(f"{label}: duplicate event content.")
        fingerprints.add(fingerprint)
        if not links:
            warnings.append(f"{eid or label}: no document association established.")
    review = events.get("review")
    if "review" in events:
        if not isinstance(review, dict):
            error("review must be an object.")
        else:
            for field in ("headline", "summary"):
                required_text(review, field, "review")
            strengths = review.get("keep_doing")
            if not isinstance(strengths, list) or any(not isinstance(s, str) or not s.strip() for s in strengths):
                error("review keep_doing must be an array of non-empty text.")
    criticisms = events.get("criticisms", [])
    if not isinstance(criticisms, list):
        error("criticisms must be an array.")
        criticisms = []
    for criticism in criticisms:
        if not isinstance(criticism, dict):
            error("Criticism must be an object.")
            continue
        for field in ("title", "problem", "consequence", "better_move"):
            required_text(criticism, field, "criticism")
        if criticism.get("basis") not in ("observed_instance", "inference"):
            error("Criticism basis must distinguish an observed instance from inference.")
        target = criticism.get("attribution")
        if target is None:
            warnings.append("Legacy criticism has no attribution; responsibility remains unknown.")
        elif not isinstance(target, str) or target not in {"user", "ai", "shared", "unknown"}:
            error("Criticism attribution must be user, ai, shared, or unknown.")
        else:
            required_text(criticism, "attribution_reason", "criticism")
        refs = criticism.get("event_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in ids for x in refs):
            error("Criticism must cite existing event IDs.")
    recommendations = events.get("recommendations")
    if not isinstance(recommendations, list):
        error("recommendations must be an array.")
        recommendations = []
    if len(recommendations) > 3:
        error("At most three recommendations are supported; prioritize rather than pad.")
    for rec in recommendations:
        if not isinstance(rec, dict):
            error("Recommendation must be an object.")
            continue
        for field in ("text", "next_check"):
            required_text(rec, field, "recommendation")
        if "verification_signal" in rec:
            required_text(rec, "verification_signal", "recommendation")
        else:
            warnings.append("Legacy recommendation has no verification_signal; effectiveness remains untested.")
        if rec.get("status") != "hypothesis":
            error("Recommendation effectiveness must remain a hypothesis.")
        refs = rec.get("event_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in ids for x in refs):
            error("Recommendation must cite existing event IDs.")
    limitations = events.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(not isinstance(x, str) or not x.strip() for x in limitations):
        error("limitations must be a non-empty array of text.")
    if manifest.get("allow_partial"):
        warnings.append("Partial input explicitly allowed; missing history remains unknown.")
    return {"valid": not errors, "run_id": manifest["run_id"], "errors": errors,
            "warnings": warnings, "events_checked": len(items), "quotes_checked": checked_quotes,
            "boundary": "Valid provenance/structure does not certify interpretation, causality, understanding, or learning."}
