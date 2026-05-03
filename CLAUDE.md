# Alliance Canvas — Claude Code project notes

This file is loaded by future Claude Code sessions running inside `~/alliance-canvas/`.
Treat it as a quick map.

## What this project is

Empire's local agent UI. Replaces Open WebUI as the chat surface for Archie (Gemma 4 E4B via Ollama) and gestures at a future where the wider Alliance (Atlas/Moro/Lyra/Palestra) can plug into the same window. v1 — Tier 1 only per the design doc at `~/atlas/docs/agentic-ui-research.md`.

## What v1 ships

- `AgentSkills` folder format (`workshop/skills/<slug>/SKILL.md`)
- `A2UI`-style card channel (` ```card ` fenced JSON → 4 typed components)
- Crew mode (one local agent + 4 visible stubs)
- Workspaces (JSON config; switching changes tool valves and active skills)
- Native tool-calling via Ollama against the existing six workshop tools

## Where things live

| Concern | File |
|---|---|
| FastAPI app + routes + WS | `backend/main.py` |
| Turn orchestration (tool-call loop) | `backend/chat_engine.py` |
| ` ```card ` fence parser (state machine) | `backend/card_parser.py` |
| AgentSkills format reader | `backend/skills_runner.py` |
| Workshop tools loader (importlib + valves) | `backend/tools_registry.py` |
| Workspace seeding + path expansion | `backend/workspaces.py` |
| SQLite for conversations | `backend/db.py` |
| Card components (4 + fallback) | `frontend/src/lib/components/cards/` |
| Chat surface | `frontend/src/lib/components/{ChatStream,MessageBubble,Composer}.svelte` |
| Crew + workspace UI | `frontend/src/lib/components/{CrewSidebar,WorkspaceSwitcher,SidePanel}.svelte` |
| State (Svelte 5 runes) | `frontend/src/lib/stores.svelte.ts` |
| Bundled config (seeded on first run) | `config/workspaces/`, `config/agents/` |
| User-mutable state | `~/.alliance-canvas/` (NOT in repo) |

## How tools work

The five workshop tools (`~/Desktop/workshop/tools/*.py`) are imported via `importlib` at workspace-load time. Each is instantiated with its `Valves` updated from `workspaces.derive_tool_valves(ws)` — which maps the workspace's named `folder_mounts` (workshop / principles_claw / vault) to each tool's specific path valves. Tools' source is never modified.

The sixth tool, `skills.py`, is loaded too but its `list_skills` / `load_skill` methods are shadowed (see `tools_registry.SHADOWED_METHODS`). The canvas-native equivalent in `skills_runner.py` reads the AgentSkills folder format.

## Card emission protocol

Each turn's system-prompt postscript (built in `chat_engine._build_system_prompt`) tells the agent to emit structured artifacts as fenced code blocks:

```
` ``card
{"type": "card", "card": "SLUTCard", "data": { … }}
` ``
```

The streaming parser in `card_parser.py` is a single-pass state machine: it holds back the last 16 bytes of token output when no fence is open (so a chunk-boundary inside `\`\`\`card` can't fool it), opens a card on the open fence, accumulates until close, parses JSON, emits a typed event. Malformed JSON falls back to a code-block + `card_parse_error` diagnostic.

## Common tasks

**Add a new workspace**: drop a JSON file into `~/.alliance-canvas/workspaces/`. The schema is in `shared/schemas/workspace.schema.json`. Reload the canvas.

**Add a new card type**: Svelte component in `frontend/src/lib/components/cards/`, branch in `CardRenderer.svelte`, optional schema entry in `shared/schemas/card.schema.json`, mention in the prompt postscript in `chat_engine._build_system_prompt`.

**Add a new agent**: JSON in `~/.alliance-canvas/agents/`. If `connected: false`, it shows as a stub. To wire up a real remote agent, you need a non-Ollama transport — that's v2.

**Modify Archie's identity**: edit `~/Desktop/workshop/modelfiles/archie.Modelfile`, then `ollama create archie -f …`. The canvas reads the current modelfile to display in the agent identity panel.

**Run smoke test**: `./scripts/smoke-test.sh` — boots backend, exercises REST + one WS turn.

## CEP-13 (ceiling investigation) applies here too

When something fails, don't declare a ceiling without checking. The empire-shape pattern is: re-read inputs, try variants, list what's available, only then report a gap. Tool failure messages echo this — they say "CEP-13 applies" rather than just "broken."

## Things that are NOT in v1

- No Open WebUI fork — separate app
- No cloud providers
- No voice
- No multi-user
- No remote-agent transport (canvas only routes to local Ollama agents)
- No mobile companion
- Full A2UI is NOT implemented — only the card channel subset
- No Live Canvas separate pane — cards are inline
- Single agent at a time — sidebar auto-shows only when 2+ connected agents exist

See `BUILD-NOTES.md` for the punt list and known gotchas.

## Don't touch

- `~/Desktop/workshop/scripts/auto_harvest.py` — runs daily
- `~/Desktop/workshop/modelfiles/archie.Modelfile` — read it, don't rewrite
- `~/Desktop/workshop/tools/*.py` — load them, don't edit
