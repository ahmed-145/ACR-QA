"""Findings router — per-finding chat (AI sidebar) and helpers (v5.0.0 Phase A.1).

Endpoints:
    GET  /v1/findings/{fid}/chat        — list persisted messages
    POST /v1/findings/{fid}/chat        — append user message, stream assistant reply (SSE)
    DELETE /v1/findings/{fid}/chat      — clear conversation
    GET  /v1/findings/chat/presets      — return preset prompt catalog

Streaming format follows EventSource conventions:
    data: {"event":"delta","text":"..."}\\n\\n
    data: {"event":"done","message_id":42,"latency_ms":812}\\n\\n
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db

router = APIRouter(prefix="/findings", tags=["findings"])

logger = logging.getLogger(__name__)


# ── Preset prompt catalog ─────────────────────────────────────────────────────

PRESET_PROMPTS: dict[str, dict[str, str]] = {
    "explain": {
        "label": "Explain",
        "prompt": (
            "Explain this finding in 3-4 sentences. Cover: what the issue is, why it matters, "
            "and the concrete consequence if shipped. Be specific to the actual code, not generic."
        ),
    },
    "exploit": {
        "label": "Show Exploit",
        "prompt": (
            "If this finding is exploitable, draft a minimal proof-of-concept payload or attack scenario. "
            "If it is not directly exploitable but enables a chain, describe the chain. "
            "If exploitation requires conditions, list them. Be honest about feasibility."
        ),
    },
    "pr_comment": {
        "label": "Draft PR Comment",
        "prompt": (
            "Draft a constructive pull-request review comment for this finding. "
            "Lead with severity and impact, then the recommended fix, then a 1-line suggestion. "
            "Tone: collegial. Length: 4-6 sentences max."
        ),
    },
    "real_in_context": {
        "label": "Real In My Context?",
        "prompt": (
            "Assess whether this is a real issue or likely a false positive given the surrounding code. "
            "Consider: is the tainted input actually attacker-controlled, is the sink reachable, "
            "are sanitizers in place. Return a verdict (TP / FP / needs-review) with your reasoning."
        ),
    },
}


def _max_history() -> int:
    try:
        return max(1, int(os.getenv("ACRQA_CHAT_HISTORY_MAX", "20")))
    except ValueError:
        return 20


def _model_name() -> str:
    return os.getenv("ACRQA_CHAT_MODEL", "llama-3.3-70b-versatile")


# ── Pydantic models ───────────────────────────────────────────────────────────


class ChatMessageOut(BaseModel):
    id: int
    finding_id: int
    role: str
    preset: str | None = None
    content: str
    model_name: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    created_at: str


class ChatMessagesOut(BaseModel):
    finding_id: int
    messages: list[ChatMessageOut]


class ChatPostRequest(BaseModel):
    preset: str | None = Field(
        default=None,
        description="Optional preset key (one of: explain / exploit / pr_comment / real_in_context).",
    )
    content: str = Field(
        default="",
        description="User-typed message. Ignored if preset is provided (preset prompt is used).",
        max_length=4000,
    )


class ChatPresetOut(BaseModel):
    key: str
    label: str
    prompt: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_system_prompt(finding: dict) -> str:
    """Compact system prompt grounded in the finding metadata."""
    rule_id = finding.get("canonical_rule_id") or finding.get("rule_id") or "UNKNOWN"
    severity = finding.get("canonical_severity") or "unknown"
    category = finding.get("category") or "unknown"
    file_path = finding.get("file_path") or "<unknown>"
    line = finding.get("line_number") or "?"
    message = finding.get("message") or ""
    snippet = (finding.get("code_snippet") or "").strip()
    snippet_block = f"\n```\n{snippet[:1200]}\n```\n" if snippet else ""

    return (
        "You are ACR-QA's security review assistant. Be concise, specific, and honest about uncertainty. "
        "Never fabricate CVE numbers or rule IDs. If unsure, say so.\n\n"
        f"## Finding under review\n"
        f"- rule: {rule_id} ({severity} / {category})\n"
        f"- location: {file_path}:{line}\n"
        f"- tool message: {message}\n"
        f"{snippet_block}"
    )


def _resolve_user_content(req: ChatPostRequest) -> tuple[str, str | None]:
    """Return (effective_content, preset_key_or_none) for the post body."""
    if req.preset:
        if req.preset not in PRESET_PROMPTS:
            raise HTTPException(status_code=400, detail=f"unknown preset: {req.preset}")
        return PRESET_PROMPTS[req.preset]["prompt"], req.preset
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content or preset is required")
    return content, None


async def _stream_assistant_reply(
    finding: dict,
    history: list[dict],
    user_content: str,
    preset: str | None,
    db: Database,
    user_id: int | None,
) -> AsyncIterator[bytes]:
    """Async generator yielding SSE-formatted bytes.

    On Groq/LLM errors we degrade to a single canned reply rather than 500ing.
    """
    # Lazy import to avoid hard failure when key pool has no keys
    try:
        from CORE.engines.explainer import ExplanationEngine

        engine = ExplanationEngine()
        client = engine.key_pool.next_client()
        model = _model_name()
        has_keys = engine.key_pool.has_keys
    except Exception as exc:  # pragma: no cover — startup-time failure
        logger.warning("LLM init failed for chat: %s", exc)
        client = None
        model = _model_name()
        has_keys = False

    started = time.time()

    if not has_keys or client is None:
        canned = (
            "AI is currently unavailable (no LLM key configured). The finding details remain "
            "visible above. Configure GROQ_API_KEY_1 to enable chat."
        )
        yield _sse({"event": "delta", "text": canned})
        msg_id = db.insert_chat_message(
            finding_id=int(finding["id"]),
            role="assistant",
            content=canned,
            preset=preset,
            user_id=user_id,
            model_name="none",
            tokens_out=0,
            latency_ms=int((time.time() - started) * 1000),
        )
        yield _sse({"event": "done", "message_id": msg_id, "latency_ms": 0})
        return

    messages = [{"role": "system", "content": _build_system_prompt(finding)}]
    for m in history[-_max_history() :]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_content})

    full_text: list[str] = []
    try:
        # Groq SDK supports streaming via stream=True
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=600,
            stream=True,
        )
        for chunk in completion:
            try:
                delta = chunk.choices[0].delta.content or ""
            except (AttributeError, IndexError):
                delta = ""
            if delta:
                full_text.append(delta)
                yield _sse({"event": "delta", "text": delta})
    except Exception as exc:
        logger.warning("LLM stream failed: %s", exc)
        fallback = (
            "AI stream interrupted. Partial reply preserved. "
            "Re-send to retry; if this persists check Groq key rotation."
        )
        full_text.append("\n\n" + fallback)
        yield _sse({"event": "delta", "text": "\n\n" + fallback})

    full = "".join(full_text).strip()
    latency_ms = int((time.time() - started) * 1000)
    msg_id = db.insert_chat_message(
        finding_id=int(finding["id"]),
        role="assistant",
        content=full or "(no content)",
        preset=preset,
        user_id=user_id,
        model_name=model,
        tokens_out=len(full.split()) if full else 0,
        latency_ms=latency_ms,
    )
    yield _sse({"event": "done", "message_id": msg_id, "latency_ms": latency_ms})


def _sse(payload: dict) -> bytes:
    """Format a single SSE line."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def _serialize_message(row: dict) -> dict:
    return {
        "id": row["id"],
        "finding_id": row["finding_id"],
        "role": row["role"],
        "preset": row.get("preset"),
        "content": row["content"],
        "model_name": row.get("model_name"),
        "tokens_in": row.get("tokens_in"),
        "tokens_out": row.get("tokens_out"),
        "latency_ms": row.get("latency_ms"),
        "created_at": str(row["created_at"]),
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/chat/presets", response_model=list[ChatPresetOut], summary="List chat preset prompts")
async def list_presets():
    """Return the 4 preset prompts shown as quick-action buttons."""
    return [{"key": k, "label": v["label"], "prompt": v["prompt"]} for k, v in PRESET_PROMPTS.items()]


# ── Time-Travel history (v5.0.0 Phase A.2) ────────────────────────────────────


@router.get(
    "/{fid}/history",
    summary="Return bounded git-history context for the finding's file/line",
)
async def get_finding_history(
    fid: int,
    max_commits: int = 50,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Walks the workspace git history (bounded by `max_commits`, capped at 200)
    and returns first_seen / commits_touching / regression_count / near_fix_commits.

    Read-only. If the workspace is not a git repo (e.g. hosted SaaS sandbox),
    returns empty history with `bounded_by_max_commits=true`.
    """
    finding = db.get_finding_by_id(fid)
    if finding is None:
        raise HTTPException(status_code=404, detail="finding not found")

    try:
        from CORE.engines.time_travel import analyze_finding_history
    except Exception as exc:
        raise HTTPException(status_code=500, detail="time-travel engine unavailable") from exc

    history = analyze_finding_history(
        repo_dir=os.getcwd(),
        file_path=finding.get("file_path") or "",
        line_number=int(finding.get("line_number") or 0) or None,
        rule_id=finding.get("canonical_rule_id"),
        max_commits=max_commits,
    )
    history["finding_id"] = fid
    return history


# ── Call Graph (v5.0.0 Phase A.1) ─────────────────────────────────────────────


@router.get(
    "/{fid}/call-graph",
    summary="Return a function-level call graph for the file containing this finding",
)
async def get_finding_call_graph(
    fid: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Returns:
        nodes: list of {id, name, reachable, is_target, is_entry}
        edges: list of {source, target}
        target: function name that contains the finding (or None)
        file_path: file analyzed

    Only Python files are supported in v5.0.0 A1; JS/TS will land in Phase B.
    """
    finding = db.get_finding_by_id(fid)
    if finding is None:
        raise HTTPException(status_code=404, detail="finding not found")

    file_path = finding.get("file_path") or ""
    line_number = int(finding.get("line_number") or 0)

    if not file_path.endswith(".py"):
        return {
            "file_path": file_path,
            "target": None,
            "nodes": [],
            "edges": [],
            "unsupported_language": True,
        }

    # Lazy import — keeps cold start fast
    try:
        from pathlib import Path as _Path

        from CORE.engines.reachability import (
            _build_call_graph,
            _detect_entry_points,
            _reachable_from,
            get_function_at_line,
        )
    except Exception as exc:
        logger.warning("reachability import failed: %s", exc)
        raise HTTPException(status_code=500, detail="reachability engine unavailable") from exc

    src_path = _Path(file_path)
    if not src_path.is_file():
        return {
            "file_path": file_path,
            "target": None,
            "nodes": [],
            "edges": [],
            "file_missing": True,
        }
    try:
        source = src_path.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="could not read source file") from None

    graph = _build_call_graph(source)
    entry_points = _detect_entry_points(source)
    reachable = _reachable_from(entry_points, graph)
    target_fn = get_function_at_line(source, line_number) if line_number else None

    nodes = []
    for fn in sorted(graph.keys()):
        nodes.append(
            {
                "id": fn,
                "name": fn,
                "reachable": fn in reachable,
                "is_target": fn == target_fn,
                "is_entry": fn in entry_points,
            }
        )
    edges = []
    fn_set = set(graph.keys())
    for caller, callees in graph.items():
        for callee in callees:
            if callee in fn_set and callee != caller:
                edges.append({"source": caller, "target": callee})

    return {
        "file_path": file_path,
        "target": target_fn,
        "entry_points": sorted(entry_points),
        "nodes": nodes,
        "edges": edges,
    }


@router.get(
    "/{fid}/chat",
    response_model=ChatMessagesOut,
    summary="List chat history for a finding",
)
async def list_chat_messages(
    fid: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if db.get_finding_by_id(fid) is None:
        raise HTTPException(status_code=404, detail="finding not found")
    rows = db.get_chat_messages(fid)
    return ChatMessagesOut(finding_id=fid, messages=[_serialize_message(r) for r in rows])


@router.delete("/{fid}/chat", summary="Clear chat history for a finding")
async def clear_chat(
    fid: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if db.get_finding_by_id(fid) is None:
        raise HTTPException(status_code=404, detail="finding not found")
    deleted = db.clear_chat_messages(fid)
    return {"finding_id": fid, "deleted": int(deleted)}


@router.post(
    "/{fid}/chat",
    summary="Send a message; stream assistant reply via SSE",
    response_class=StreamingResponse,
)
async def post_chat(
    fid: int,
    body: ChatPostRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    finding = db.get_finding_by_id(fid)
    if finding is None:
        raise HTTPException(status_code=404, detail="finding not found")

    user_content, preset = _resolve_user_content(body)
    user_id = user.get("id") if isinstance(user, dict) else None
    history = db.get_chat_messages(fid)

    # Persist the user turn before streaming
    db.insert_chat_message(
        finding_id=fid,
        role="user",
        content=user_content,
        preset=preset,
        user_id=user_id,
    )

    return StreamingResponse(
        _stream_assistant_reply(finding, history, user_content, preset, db, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
