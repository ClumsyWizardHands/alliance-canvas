"""
Turn orchestrator.

Drives one user-message → assistant-response cycle. Streams events to a single
async sink (a WebSocket, in practice). Handles tool-calling loops natively
through Ollama's `tools` parameter; any tool call is executed locally and the
result is fed back into the model.

Card detection is layered on top of the assistant content stream — see
card_parser.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

from . import db, ollama_client, tools_registry
from .card_parser import CardStreamParser, strip_cards_from_text
from .skills_runner import list_skills, load_skill, index_to_dict, skill_to_dict
from pathlib import Path


log = logging.getLogger(__name__)

# Cap how many tool-call rounds we'll do per turn before giving up. Without
# this, a model that emits a tool call on every step can loop forever.
MAX_TOOL_ROUNDS = 8


@dataclass
class TurnContext:
    workspace: dict
    agent: dict
    conversation_id: int
    user_text: str
    loaded_tools: dict[str, tools_registry.LoadedTool]
    tool_schemas: list[dict]
    skills_dir: Path


def _build_system_prompt(agent: dict, workspace: dict, skills_dir: Path) -> str:
    """
    Assemble the agent's effective system prompt:
      1. The Modelfile's SYSTEM block (already loaded by Ollama via the model).
      2. A per-turn postscript covering the active workspace + canvas conventions
         (active skills/CEPs, card-emission protocol, alliance presence).
    Ollama prepends its own model SYSTEM, so we only return the postscript here
    — it's appended as the first user-visible system message in the stream.
    """
    workspace_name = workspace.get("name", "Default")
    crew = workspace.get("default_crew", [])
    active_skills = workspace.get("active_skills", [])
    active_ceps = workspace.get("active_ceps", [])

    # Inline the available skills' descriptions so the model knows what's loadable
    # without burning a list_skills round-trip on every turn.
    skill_lines = []
    for idx in list_skills(skills_dir, active_filter=active_skills or None):
        skill_lines.append(f"  - `{idx.slug}` — {idx.description}")
    skills_block = "\n".join(skill_lines) if skill_lines else "  (none active)"

    cep_lines = [f"  - `{c}`" for c in active_ceps] if active_ceps else ["  (none active)"]
    cep_block = "\n".join(cep_lines)

    crew_block = ", ".join(crew) if crew else "(none)"

    extra = (agent.get("system_prompt_extra") or "").strip()

    parts = [
        f"You are speaking inside Alliance Canvas, the empire local agent UI.",
        f"Active workspace: **{workspace_name}**.",
        f"Crew present: {crew_block}.",
        "",
        "Active skills (loadable via `load_skill`):",
        skills_block,
        "",
        "Active CEPs (loadable via `load_principle`):",
        cep_block,
        "",
        "## Card emission",
        "When you produce a structured artifact (a SLUT, a CEP routing decision, a harvest summary, a quoted principle, an alliance handoff), emit it as a fenced code block with language `card` containing JSON of shape:",
        "",
        "```card",
        '{"type": "card", "card": "SLUTCard", "data": { ... }}',
        "```",
        "",
        "Available card types: `SLUTCard`, `CEPRoutingCard`, `HarvestSummaryCard`, `PrincipleQuoteCard`. The canvas renders these as visual cards inline. Plain prose continues to render as markdown — use cards only when the content is genuinely structured. If unsure of the JSON shape, fall back to plain markdown — the canvas degrades gracefully.",
        "",
        "## Handoff",
        "When you recommend handing off to another Alliance member, name the agent explicitly. The UI will surface it as a clickable handoff chip.",
    ]
    if extra:
        parts.append("")
        parts.append("## Operator additions")
        parts.append(extra)
    return "\n".join(parts)


def _history_for_ollama(conversation_id: int, system_postscript: str) -> list[dict]:
    """Translate stored messages into Ollama chat-message shape."""
    out: list[dict] = [{"role": "system", "content": system_postscript}]
    for m in db.list_messages(conversation_id):
        role = m["role"]
        if role == "tool":
            out.append({"role": "tool", "content": m["content"], "tool_call_id": m.get("tool_call_id") or ""})
            continue
        msg: dict[str, Any] = {"role": role, "content": m["content"]}
        if m.get("tool_calls"):
            msg["tool_calls"] = m["tool_calls"]
        out.append(msg)
    return out


async def run_turn(ctx: TurnContext, emit: Callable[[dict], Awaitable[None]]) -> int:
    """
    Drive a single turn. Returns the assistant message id once persisted.

    Events emitted to `emit`:
      {type: "token",          content: str}
      {type: "card",           card: str, data: dict}
      {type: "card_start"}
      {type: "card_parse_error", error: str, raw: str}
      {type: "tool_call_start", name: str, args: dict, call_id: str}
      {type: "tool_call_end",   name: str, output: str, call_id: str}
      {type: "tool_round_limit", rounds: int}
      {type: "error",          message: str}
      {type: "done",           message_id: int}
    """
    agent = ctx.agent
    model = agent.get("model") or "archie"
    options = dict(ctx.workspace.get("model_params") or {})

    system_postscript = _build_system_prompt(agent, ctx.workspace, ctx.skills_dir)
    db.append_message(ctx.conversation_id, role="user", content=ctx.user_text)
    messages = _history_for_ollama(ctx.conversation_id, system_postscript)

    parser = CardStreamParser()
    accumulated_content = ""
    final_message_id: int | None = None

    for round_idx in range(MAX_TOOL_ROUNDS):
        round_content = ""
        round_tool_calls: list[dict] = []

        try:
            async for chunk in ollama_client.chat_stream(
                model=model,
                messages=messages,
                tools=ctx.tool_schemas or None,
                options=options or None,
            ):
                msg = chunk.get("message") or {}
                content_piece = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []
                done = bool(chunk.get("done"))

                if content_piece:
                    round_content += content_piece
                    accumulated_content += content_piece
                    for ev in parser.feed(content_piece):
                        await emit(ev)

                if tool_calls:
                    round_tool_calls.extend(tool_calls)

                if done:
                    break
        except ollama_client.OllamaError as e:
            await emit({"type": "error", "message": str(e)})
            return -1

        # Flush any held-back tail from this round's content into the parser
        # only if the model is fully done with this round (no tool calls coming).
        if not round_tool_calls:
            for ev in parser.flush():
                await emit(ev)

            # Persist final assistant message + cards
            cleaned = strip_cards_from_text(accumulated_content)
            final_message_id = db.append_message(
                ctx.conversation_id,
                role="assistant",
                content=cleaned,
                agent=agent.get("name"),
                tool_calls=None,
            )
            for c in parser.cards_emitted:
                db.append_card(final_message_id, c["card"], c["data"])
            await emit({"type": "done", "message_id": final_message_id})
            return final_message_id

        # Tool-call round: persist the assistant turn that contains the calls,
        # execute each call, append tool results, loop.
        assistant_msg_id = db.append_message(
            ctx.conversation_id,
            role="assistant",
            content=round_content,
            agent=agent.get("name"),
            tool_calls=round_tool_calls,
        )
        # Mirror to the Ollama messages list for the next round
        ollama_assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": round_content,
            "tool_calls": round_tool_calls,
        }
        messages.append(ollama_assistant_msg)

        for tc in round_tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
            call_id = tc.get("id") or f"call_{assistant_msg_id}_{name}"

            await emit({"type": "tool_call_start", "name": name, "args": args, "call_id": call_id})

            method = tools_registry.find_method(ctx.loaded_tools, name)
            if method is None:
                # Special case: list_skills / load_skill are canvas-native
                output = _handle_canvas_native(name, args, ctx)
                if output is None:
                    output = (
                        f"No tool registered for '{name}'. CEP-13: check the active "
                        f"workspace's tool allowlist and the workshop tools directory. "
                        f"If this is genuinely missing, surface to Alex."
                    )
            else:
                output = tools_registry.call_method(method, args)

            await emit({"type": "tool_call_end", "name": name, "output": output, "call_id": call_id})

            db.append_message(
                ctx.conversation_id,
                role="tool",
                content=output,
                tool_call_id=call_id,
                tool_name=name,
            )
            messages.append({"role": "tool", "content": output, "tool_call_id": call_id})

    await emit({"type": "tool_round_limit", "rounds": MAX_TOOL_ROUNDS})
    if final_message_id is None:
        # Couldn't reach a final message — persist what we have
        final_message_id = db.append_message(
            ctx.conversation_id,
            role="assistant",
            content=accumulated_content + "\n\n_(tool round limit reached)_",
            agent=agent.get("name"),
        )
    await emit({"type": "done", "message_id": final_message_id})
    return final_message_id


def _handle_canvas_native(name: str, args: dict, ctx: TurnContext) -> str | None:
    """Canvas-native tool implementations that shadow workshop equivalents."""
    if name == "list_skills":
        idx = list_skills(ctx.skills_dir, active_filter=ctx.workspace.get("active_skills") or None)
        if not idx:
            return f"No active skills in workspace '{ctx.workspace.get('name')}'."
        out = ["# Loadable Skills (Alliance Canvas — AgentSkills format)\n"]
        for s in idx:
            emoji = (s.emoji + " ") if s.emoji else ""
            out.append(f"- {emoji}`{s.slug}` — {s.description}")
            if s.flat_warning:
                out.append(f"  _(legacy flat-file format; {s.flat_warning})_")
        return "\n".join(out)
    if name == "load_skill":
        slug = args.get("slug") or args.get("name") or ""
        s = load_skill(ctx.skills_dir, slug)
        if not s:
            indices = list_skills(ctx.skills_dir, active_filter=ctx.workspace.get("active_skills") or None)
            available = ", ".join(i.slug for i in indices) or "(none)"
            return (
                f"No skill matched slug '{slug}'. "
                f"Available in active workspace: {available}. "
                f"CEP-13: re-check the slug or list_skills first."
            )
        return f"_(skill: {s.slug}{' [folder]' if s.is_folder_format else ' [flat]'})_\n\n{s.body}"
    return None
