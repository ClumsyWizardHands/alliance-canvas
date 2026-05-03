"""
FastAPI entry point.

Endpoints:
  GET  /api/health                — version, Ollama reachable, workspace count
  GET  /api/workspaces            — list workspaces
  GET  /api/workspaces/{name}     — read one
  PUT  /api/workspaces/{name}     — write one
  GET  /api/agents                — list agent configs (with inlined modelfile text)
  GET  /api/agents/{name}         — read one
  GET  /api/skills                — list active skills for a workspace
  GET  /api/skills/{slug}         — read full skill body
  GET  /api/principles            — list principles (kernel/rgt/protocols)
  GET  /api/principles/{slug}     — read one principle
  GET  /api/ledger                — last N entries from ledger.jsonl
  GET  /api/conversations         — list conversations (optionally by workspace)
  GET  /api/conversations/{id}    — read messages + cards
  POST /api/chat                  — start a turn; returns turn_id + ws_url
  WS   /api/chat/stream/{turn_id} — stream tokens, tool calls, cards
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import agents as agents_mod
from . import db, ledger, ollama_client, skills_runner, tools_registry, workspaces
from .chat_engine import TurnContext, run_turn
from .config import (
    BACKEND_PORT,
    FRONTEND_PORT,
    PRINCIPLES_CLAW_DIR,
    VERSION,
    ensure_user_state_dirs,
)


log = logging.getLogger("alliance_canvas")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


# Pending turns awaiting their WS connection. Each entry holds the materials
# needed to drive the turn once the WebSocket attaches.
_PENDING_TURNS: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_user_state_dirs()
    db.init_db()
    workspaces.seed_defaults_if_empty()
    agents_mod.seed_defaults_if_empty()
    log.info("Alliance Canvas backend %s ready on :%s (frontend expected on :%s)", VERSION, BACKEND_PORT, FRONTEND_PORT)
    yield


app = FastAPI(title="Alliance Canvas", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{FRONTEND_PORT}", f"http://127.0.0.1:{FRONTEND_PORT}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Health -----------------------------------------------------------

@app.get("/api/health")
async def health():
    ok, message = await ollama_client.is_reachable()
    return {
        "version": VERSION,
        "ollama": {"reachable": ok, "message": message},
        "workspace_count": len(workspaces.list_workspaces()),
        "agent_count": len(agents_mod.list_agents()),
        "ledger": ledger.ledger_meta(),
    }


# ---------- Workspaces -------------------------------------------------------

@app.get("/api/workspaces")
async def get_workspaces():
    return {"workspaces": workspaces.list_workspaces()}


@app.get("/api/workspaces/{name}")
async def get_one_workspace(name: str):
    ws = workspaces.get_workspace(name)
    if not ws:
        raise HTTPException(404, f"Workspace '{name}' not found")
    return ws


class WorkspacePut(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None
    folder_mounts: dict[str, str] | list[str] | None = None
    active_skills: list[str] | None = None
    active_ceps: list[str] | None = None
    active_tools: list[str] | None = None
    model_params: dict[str, Any] | None = None
    default_crew: list[str] | None = None
    tool_valves: dict[str, dict[str, Any]] | None = None


@app.put("/api/workspaces/{name}")
async def put_workspace(name: str, body: WorkspacePut):
    data = body.model_dump(exclude_none=True)
    workspaces.save_workspace(name, data)
    return workspaces.get_workspace(name)


# ---------- Agents -----------------------------------------------------------

@app.get("/api/agents")
async def get_agents():
    return {"agents": agents_mod.list_agents()}


@app.get("/api/agents/{name}")
async def get_one_agent(name: str):
    a = agents_mod.get_agent(name)
    if not a:
        raise HTTPException(404, f"Agent '{name}' not found")
    return a


# ---------- Skills -----------------------------------------------------------

@app.get("/api/skills")
async def get_skills(workspace: str = "Default"):
    ws = workspaces.get_workspace(workspace)
    if not ws:
        raise HTTPException(404, f"Workspace '{workspace}' not found")
    skills_dir = Path(ws["folder_mounts"].get("workshop", "")) / "skills"
    indices = skills_runner.list_skills(skills_dir, active_filter=ws.get("active_skills") or None)
    return {
        "workspace": workspace,
        "skills_dir": str(skills_dir),
        "skills": [skills_runner.index_to_dict(i) for i in indices],
    }


@app.get("/api/skills/{slug}")
async def get_one_skill(slug: str, workspace: str = "Default"):
    ws = workspaces.get_workspace(workspace)
    if not ws:
        raise HTTPException(404, f"Workspace '{workspace}' not found")
    skills_dir = Path(ws["folder_mounts"].get("workshop", "")) / "skills"
    s = skills_runner.load_skill(skills_dir, slug)
    if not s:
        raise HTTPException(404, f"Skill '{slug}' not found in workspace '{workspace}'")
    return skills_runner.skill_to_dict(s)


# ---------- Principles -------------------------------------------------------

@app.get("/api/principles")
async def get_principles(workspace: str = "Default"):
    """List principles from kernel + rgt + protocols, with stack labels for the UI."""
    ws = workspaces.get_workspace(workspace)
    if not ws:
        raise HTTPException(404, f"Workspace '{workspace}' not found")
    pc_root = Path(ws["folder_mounts"].get("principles_claw") or PRINCIPLES_CLAW_DIR)
    stacks = [
        ("kernel", pc_root / "principles" / "kernel"),
        ("rgt", pc_root / "principles" / "rgt"),
        ("applied", pc_root / "principles" / "applied"),
        ("protocols", pc_root / "protocols"),
    ]
    out = []
    for stack_name, stack_path in stacks:
        if not stack_path.exists():
            continue
        for f in sorted(stack_path.glob("*.md")):
            if f.stem in ("README", "INSTRUCTIONS"):
                continue
            title = f.stem.replace("-", " ")
            try:
                first = f.read_text().split("\n", 1)[0]
                if first.startswith("# "):
                    title = first.lstrip("# ").strip()
            except Exception:
                pass
            out.append(
                {
                    "slug": f.stem,
                    "title": title,
                    "stack": stack_name,
                    "path": str(f.relative_to(pc_root)),
                }
            )
    return {"workspace": workspace, "principles": out}


@app.get("/api/principles/{slug}")
async def get_one_principle(slug: str, workspace: str = "Default"):
    ws = workspaces.get_workspace(workspace)
    if not ws:
        raise HTTPException(404, f"Workspace '{workspace}' not found")
    pc_root = Path(ws["folder_mounts"].get("principles_claw") or PRINCIPLES_CLAW_DIR)
    stacks = [
        ("kernel", pc_root / "principles" / "kernel"),
        ("rgt", pc_root / "principles" / "rgt"),
        ("applied", pc_root / "principles" / "applied"),
        ("protocols", pc_root / "protocols"),
    ]
    for stack_name, stack_path in stacks:
        f = stack_path / f"{slug}.md"
        if f.exists():
            return {"slug": slug, "stack": stack_name, "body": f.read_text()}
    raise HTTPException(404, f"Principle '{slug}' not found in any active stack")


# ---------- Ledger -----------------------------------------------------------

@app.get("/api/ledger")
async def get_ledger(n: int = 50):
    return {
        "meta": ledger.ledger_meta(),
        "entries": ledger.read_tail(n),
    }


# ---------- Conversations ----------------------------------------------------

@app.get("/api/conversations")
async def get_conversations(workspace: str | None = None):
    return {"conversations": db.list_conversations(workspace=workspace)}


@app.get("/api/conversations/{conversation_id}")
async def get_one_conversation(conversation_id: int):
    msgs = db.list_messages(conversation_id)
    return {"id": conversation_id, "messages": msgs}


# ---------- Chat -------------------------------------------------------------

class ChatStart(BaseModel):
    workspace: str = "Default"
    agent: str = "archie"
    message: str
    conversation_id: int | None = None


@app.post("/api/chat")
async def start_chat(body: ChatStart):
    ws = workspaces.get_workspace(body.workspace)
    if not ws:
        raise HTTPException(404, f"Workspace '{body.workspace}' not found")
    agent = agents_mod.get_agent(body.agent)
    if not agent:
        raise HTTPException(404, f"Agent '{body.agent}' not found")
    if not agent.get("connected", True):
        raise HTTPException(
            409,
            f"Agent '{body.agent}' is not connected on this machine. "
            f"v1 only routes to locally-running agents. Try 'archie' or surface "
            f"to Alex to wire up the gateway path."
        )

    conv_id = body.conversation_id or db.create_conversation(workspace=body.workspace, title=body.message[:60])

    # Pre-load tools and schemas now so we can fail fast on misconfiguration
    valve_overrides = workspaces.derive_tool_valves(ws)
    loaded_tools = tools_registry.load_tools_for_workspace(valve_overrides)
    allowlist = set(agent.get("tool_allowlist") or []) or None
    tool_schemas = tools_registry.to_ollama_tool_schemas(loaded_tools, allowlist=allowlist)

    # Always include canvas-native shadowed methods so the agent can call them
    # by name even though they don't exist in workshop/tools/skills.py with our
    # AgentSkills format. We synthesize their schemas inline.
    tool_schemas.extend(_canvas_native_schemas())

    skills_dir = Path(ws["folder_mounts"].get("workshop", "")) / "skills"

    turn_id = uuid.uuid4().hex[:16]
    _PENDING_TURNS[turn_id] = {
        "ws": ws,
        "agent": agent,
        "user_text": body.message,
        "conversation_id": conv_id,
        "loaded_tools": loaded_tools,
        "tool_schemas": tool_schemas,
        "skills_dir": skills_dir,
    }
    return {
        "turn_id": turn_id,
        "conversation_id": conv_id,
        "ws_url": f"/api/chat/stream/{turn_id}",
        "tools_loaded": [
            {"tool_id": tid, "method_count": len(lt.methods), "error": lt.error}
            for tid, lt in loaded_tools.items()
        ],
    }


def _canvas_native_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_skills",
                "description": (
                    "List loadable skills available in the active workspace (AgentSkills format). "
                    "Returns slugs and descriptions you can pass to load_skill."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "Load the full body of a skill. Pass a slug from list_skills. "
                    "Skills are larger than principles — load deliberately and operate inside the frame."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "Skill slug, e.g. 'slut-harvest'."}
                    },
                    "required": ["slug"],
                },
            },
        },
    ]


@app.websocket("/api/chat/stream/{turn_id}")
async def chat_stream(ws: WebSocket, turn_id: str):
    await ws.accept()
    pending = _PENDING_TURNS.pop(turn_id, None)
    if not pending:
        await ws.send_json({"type": "error", "message": f"Turn '{turn_id}' not found or already started."})
        await ws.close()
        return

    ctx = TurnContext(
        workspace=pending["ws"],
        agent=pending["agent"],
        conversation_id=pending["conversation_id"],
        user_text=pending["user_text"],
        loaded_tools=pending["loaded_tools"],
        tool_schemas=pending["tool_schemas"],
        skills_dir=pending["skills_dir"],
    )

    async def emit(event: dict):
        try:
            await ws.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            raise

    try:
        await run_turn(ctx, emit)
    except WebSocketDisconnect:
        log.warning("Client disconnected mid-turn (turn_id=%s)", turn_id)
    except Exception as e:
        log.exception("Turn failed (turn_id=%s)", turn_id)
        try:
            await ws.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# ---------- CLI entry -------------------------------------------------------

def main():
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=BACKEND_PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
