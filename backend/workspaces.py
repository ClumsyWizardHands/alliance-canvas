"""
Workspace CRUD.

A workspace is a JSON config that bundles: folder_mounts (named anchors the
tools resolve from), active_skills, active_ceps, model_params, default_crew,
and presentation metadata (color, description).

User workspaces live at ~/.alliance-canvas/workspaces/. Bundled defaults live
in the repo at config/workspaces/. On first run, bundled defaults are seeded
into the user dir if it's empty.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from .config import (
    BUNDLED_WORKSPACES_DIR,
    USER_WORKSPACES_DIR,
    WORKSHOP_DIR,
    PRINCIPLES_CLAW_DIR,
    DEFAULT_VAULT_DIR,
)


REQUIRED_FIELDS = ("name", "folder_mounts", "active_skills", "active_ceps", "model_params", "default_crew")


def _expand_path(p: str) -> str:
    """Expand ~ and env vars; leave the rest as-is."""
    return os.path.expandvars(os.path.expanduser(p))


def seed_defaults_if_empty() -> None:
    """If the user's workspaces dir is empty, copy bundled defaults in."""
    USER_WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    if any(USER_WORKSPACES_DIR.glob("*.json")):
        return
    if not BUNDLED_WORKSPACES_DIR.exists():
        return
    for src in BUNDLED_WORKSPACES_DIR.glob("*.json"):
        shutil.copy2(src, USER_WORKSPACES_DIR / src.name)


def list_workspaces() -> list[dict]:
    seed_defaults_if_empty()
    out = []
    for f in sorted(USER_WORKSPACES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            data["_file"] = f.name
            out.append(data)
        except Exception as e:
            out.append({"name": f.stem, "_error": str(e), "_file": f.name})
    return out


def get_workspace(name: str) -> dict | None:
    seed_defaults_if_empty()
    f = USER_WORKSPACES_DIR / f"{name}.json"
    if not f.exists():
        # Fall back to slugified lookup
        for candidate in USER_WORKSPACES_DIR.glob("*.json"):
            data = json.loads(candidate.read_text())
            if data.get("name") == name:
                return resolve_workspace(data)
        return None
    return resolve_workspace(json.loads(f.read_text()))


def resolve_workspace(data: dict) -> dict:
    """Expand paths in folder_mounts; leave other fields as-is."""
    mounts = data.get("folder_mounts", {})
    if isinstance(mounts, list):
        # Backwards compat: convert flat list to named map by best-guess
        # (workshop / principles_claw / vault are the canonical anchors)
        named: dict[str, str] = {}
        for p in mounts:
            ep = _expand_path(p)
            if "workshop" in ep.lower():
                named["workshop"] = ep
            elif "principles-claw" in ep.lower() or "principles_claw" in ep.lower():
                named["principles_claw"] = ep
            elif "obsidian" in ep.lower() or "vault" in ep.lower() or "second-brain" in ep.lower():
                named["vault"] = ep
            else:
                named.setdefault("other", ep)
        data["folder_mounts"] = named
    else:
        data["folder_mounts"] = {k: _expand_path(v) for k, v in mounts.items()}
    return data


def save_workspace(name: str, data: dict) -> None:
    USER_WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data["name"] = name
    f = USER_WORKSPACES_DIR / f"{name}.json"
    f.write_text(json.dumps(data, indent=2) + "\n")


def derive_tool_valves(workspace: dict) -> dict[str, dict[str, Any]]:
    """
    Auto-derive per-tool valve overrides from workspace.folder_mounts.

    Returns a mapping of tool_id → {valve_name: value}. Each tool's
    instantiated Tools() Valves model is updated with these overrides at
    workspace load time. If workspace.tool_valves is set, it merges on top
    (explicit overrides win).
    """
    mounts = workspace.get("folder_mounts", {})
    workshop = mounts.get("workshop", str(WORKSHOP_DIR))
    pc = mounts.get("principles_claw", str(PRINCIPLES_CLAW_DIR))
    vault = mounts.get("vault", str(DEFAULT_VAULT_DIR))

    auto: dict[str, dict[str, Any]] = {
        "ecosystem_glossary": {
            "GLOSSARY_PATH": str(Path(workshop) / "glossary" / "ecosystem-glossary.json"),
        },
        "principles_library": {
            "KERNEL_PATH":    str(Path(pc) / "principles" / "kernel"),
            "RGT_PATH":       str(Path(pc) / "principles" / "rgt"),
            "PROTOCOLS_PATH": str(Path(pc) / "protocols"),
        },
        "skills": {
            "SKILLS_PATH": str(Path(workshop) / "skills"),
        },
        "vault": {
            "VAULT_PATH": vault,
        },
        "transcripts": {
            "TRANSCRIPT_DIR": str(Path(vault) / "transcripts"),
        },
        "web_search": {
            # SearXNG default in the Open WebUI tool is host.docker.internal:8888.
            # Native canvas runs on host directly — talk to localhost.
            "SEARXNG_URL": "http://localhost:8888",
        },
    }

    explicit = workspace.get("tool_valves") or {}
    for tool_id, overrides in explicit.items():
        auto.setdefault(tool_id, {}).update(overrides)
    return auto
