"""
Agent config CRUD.

An agent config is a JSON file describing one Alliance member's runtime shape:
ollama model, modelfile pointer (for sidebar transparency), color/avatar,
tool allowlist, handoff matrix, and a connectivity flag (`connected: false`
means stub — UI shows grayed-out, never routes Ollama calls).

User agents live at ~/.alliance-canvas/agents/. Bundled defaults at
config/agents/. Seeding behavior matches workspaces.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import BUNDLED_AGENTS_DIR, USER_AGENTS_DIR, MODELFILES_DIR


def seed_defaults_if_empty() -> None:
    USER_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    if any(USER_AGENTS_DIR.glob("*.json")):
        return
    if not BUNDLED_AGENTS_DIR.exists():
        return
    for src in BUNDLED_AGENTS_DIR.glob("*.json"):
        shutil.copy2(src, USER_AGENTS_DIR / src.name)


def list_agents() -> list[dict]:
    seed_defaults_if_empty()
    out = []
    for f in sorted(USER_AGENTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            out.append(_with_modelfile(data))
        except Exception as e:
            out.append({"name": f.stem, "_error": str(e)})
    return out


def get_agent(name: str) -> dict | None:
    seed_defaults_if_empty()
    f = USER_AGENTS_DIR / f"{name}.json"
    if not f.exists():
        for candidate in USER_AGENTS_DIR.glob("*.json"):
            data = json.loads(candidate.read_text())
            if data.get("name") == name:
                return _with_modelfile(data)
        return None
    return _with_modelfile(json.loads(f.read_text()))


def _with_modelfile(data: dict) -> dict:
    """Inline the modelfile contents if a path is set, so the UI can show it."""
    mf_name = data.get("modelfile")
    if mf_name:
        mf_path = MODELFILES_DIR / mf_name
        if mf_path.exists():
            try:
                data["_modelfile_text"] = mf_path.read_text()
            except Exception:
                data["_modelfile_text"] = None
        else:
            data["_modelfile_text"] = None
    return data
