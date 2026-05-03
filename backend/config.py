"""
Central configuration for Alliance Canvas backend.

Resolves all paths once at startup so other modules import constants instead
of recomputing. Per-workspace overrides happen at workspace-load time, not here.
"""

from __future__ import annotations

import os
from pathlib import Path

VERSION = "0.1.0"

# Server
BACKEND_PORT = int(os.environ.get("ALLIANCE_BACKEND_PORT", "5181"))
FRONTEND_PORT = int(os.environ.get("ALLIANCE_FRONTEND_PORT", "5180"))

# Ollama
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "300"))  # seconds, generous for long generations

# Filesystem anchors — the canvas's view of the host filesystem.
# Workspace folder_mounts override these; these are defaults for "Default" workspace.
HOME = Path.home()
WORKSHOP_DIR = HOME / "Desktop" / "workshop"
PRINCIPLES_CLAW_DIR = HOME / "principles-claw"
DEFAULT_VAULT_DIR = HOME / "Obsidian" / "empire-second-brain"
LEDGER_PATH = HOME / ".principles-claw" / "memory" / "ledger.jsonl"

# Repo-level (bundled) config
REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_WORKSPACES_DIR = REPO_ROOT / "config" / "workspaces"
BUNDLED_AGENTS_DIR = REPO_ROOT / "config" / "agents"

# User-mutable state
USER_STATE_DIR = HOME / ".alliance-canvas"
USER_WORKSPACES_DIR = USER_STATE_DIR / "workspaces"
USER_AGENTS_DIR = USER_STATE_DIR / "agents"
USER_LOGS_DIR = USER_STATE_DIR / "logs"
SQLITE_PATH = USER_STATE_DIR / "db.sqlite"

# Modelfiles (read-only — surfaced to the UI for transparency)
MODELFILES_DIR = WORKSHOP_DIR / "modelfiles"

# Tools (read at workspace-load time, instantiated per workspace)
TOOLS_DIR = WORKSHOP_DIR / "tools"


def ensure_user_state_dirs() -> None:
    """Create user-mutable state directories on first run."""
    for d in (USER_STATE_DIR, USER_WORKSPACES_DIR, USER_AGENTS_DIR, USER_LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
