# Alliance Canvas

Local desktop chat UI for Ollama-backed agents — built for Gemma but model-agnostic. Replaces Open WebUI as the chat surface, adds:

- **AgentSkills** folder format (markdown skills with YAML frontmatter)
- **A2UI-style cards** — agents emit structured JSON, the canvas renders it as visual components inline
- **Workspaces** — switch posture (which folders are visible, which skills/CEPs are active, which model params apply) without restarting
- **Native tool-calling** through Ollama — auto-loads Open-WebUI-shaped Python tools and exposes them via the `tools` API

Single-user, localhost-only, no auth, no cloud.

> Originally built for [Archie](https://gemma4lovessluts.empire.email) — a Gemma 4 E4B agent with a specific identity. Ships with Archie's config as the example. **See [SETUP.md](./SETUP.md) to swap in your own model.**

## Quick start

```bash
git clone https://github.com/ClumsyWizardHands/alliance-canvas.git
cd alliance-canvas
./scripts/start.sh           # boots backend on :5181, frontend on :5180
open http://localhost:5180
```

Requires:
- macOS / Linux / WSL2
- [Ollama](https://ollama.com/download) running on `:11434`
- An installed model — by default the bundled config expects `archie:latest`. To use a different model, edit `~/.alliance-canvas/agents/archie.json` after first run, or follow [SETUP.md](./SETUP.md) to add your own.

## Architecture (one screen)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Browser (localhost:5180)                                                │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ SvelteKit SPA                                                       │ │
│ │   TopBar (workspace switcher · agent badge · ledger/skills toggle)  │ │
│ │   ChatStream (token stream · cards inline · tool-call chips)        │ │
│ │   SidePanel (ledger | skills | principles | agent identity)         │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                              ▲                                          │
│                              │  /api/* via Vite proxy                   │
│                              ▼                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ FastAPI backend (localhost:5181)                                    │ │
│ │   POST /api/chat → WS /api/chat/stream/{turn_id}                    │ │
│ │   chat_engine ──► ollama_client ──► Ollama (:11434)                 │ │
│ │       ├─► tools_registry  (importlib + per-workspace valves)        │ │
│ │       ├─► skills_runner   (AgentSkills format)                      │ │
│ │       └─► card_parser     (strips ```card``` fences from stream)    │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## What ships

| Feature | Where it lives |
|---|---|
| **AgentSkills format** | `backend/skills_runner.py` reads `<skills_dir>/<slug>/SKILL.md` with YAML frontmatter. Flat `.md` files at the root still work (with a warning). |
| **A2UI card channel** | `backend/card_parser.py` extracts ` ```card ` fenced JSON blocks from the assistant stream and routes them as separate WS events. Frontend has component-keyed renderers in `frontend/src/lib/components/cards/`. Four cards ship: `SLUTCard`, `CEPRoutingCard`, `HarvestSummaryCard`, `PrincipleQuoteCard`. Unknown types fall back to a generic JSON view. |
| **Workspaces** | JSON files at `~/.alliance-canvas/workspaces/` — bundled defaults seeded from `config/workspaces/` on first run. Switching a workspace re-derives tool valves so the agent's "view of the world" changes. |
| **Tool autoloader** | `backend/tools_registry.py` imports any `class Tools` Python module from `<workshop>/tools/`, parses docstrings for tool descriptions and parameter schemas, registers them with Ollama. |

## Repo layout

```
alliance-canvas/
  backend/                  # FastAPI app
    main.py                 # routes + WS
    chat_engine.py          # turn orchestrator (token stream + tool-call loop)
    tools_registry.py       # importlib loader for workshop tools
    skills_runner.py        # AgentSkills folder format reader
    card_parser.py          # ```card``` fence parser (state machine)
    ollama_client.py        # async streaming client
  frontend/                 # SvelteKit + Tailwind
    src/lib/components/     # Composer, ChatStream, MessageBubble, SidePanel,
                            #   CrewSidebar, WorkspaceSwitcher, ToolCallChip
    src/lib/components/cards/ # 4 card types + FallbackCard
  shared/schemas/           # JSON schemas for workspace + cards
  config/                   # bundled defaults (seeded into ~/.alliance-canvas/)
    workspaces/             # Default.json, Daily Harvest.json
    agents/                 # archie.json + example-myagent.json.example
  scripts/
    start.sh                # boot backend + frontend dev servers
    dev.sh                  # same, with backend hot reload
    smoke-test.sh           # boots backend, exercises REST + one WS turn
  SETUP.md                  # how to wire up your own agent
  BUILD-NOTES.md            # design decisions, known gotchas
  CLAUDE.md                 # for Claude Code agents working on this repo
```

User-mutable state lives at `~/.alliance-canvas/`:

```
~/.alliance-canvas/
  workspaces/    # editable copies of config/workspaces/
  agents/        # editable copies of config/agents/
  db.sqlite      # conversation history
  logs/          # backend.log, frontend.log
```

## Card-emission convention (what the agent sees)

Every turn, the system prompt is appended with:

> When you produce a structured artifact (a SLUT, a CEP routing decision, a harvest summary, a quoted principle), emit it as a fenced code block with language `card` containing JSON of shape `{"type":"card", "card":"SLUTCard", "data":{...}}`. Available card types: SLUTCard, CEPRoutingCard, HarvestSummaryCard, PrincipleQuoteCard. The canvas renders these as visual cards inline. Plain prose continues to render as markdown — use cards only when the content is genuinely structured.

If the JSON is malformed, the canvas falls back to rendering the raw block as a code chunk and emits a `card_parse_error` diagnostic.

## Smoke test

```bash
./scripts/smoke-test.sh
```

Boots the backend on :5181, exercises every REST endpoint, runs one streaming turn against your active agent via WebSocket, and reports pass/fail.

## Set it up for your own agent

See [SETUP.md](./SETUP.md). The TL;DR is: copy `config/agents/example-myagent.json.example` to `~/.alliance-canvas/agents/<yourname>.json`, set the Ollama model tag, restart.

## What's not in v1

- Multi-channel adapters (Discord/Slack)
- Cloud model providers — local-only by design
- Voice / TTS / STT
- Plugin marketplace
- Multi-user auth
- Full A2UI protocol — only the focused card subset
- Live Canvas pane (separate window) — cards are inline in chat
- Mobile companion

See [BUILD-NOTES.md](./BUILD-NOTES.md) for what got cut and why.

## License

MIT. See [LICENSE](./LICENSE).

## Origin

Built by Alex Crowell at empire as the chat surface for [Archie](https://github.com/ClumsyWizardHands/alliance-canvas), the local Gemma 4 ecosystem agent. The bundled card types (`SLUTCard`, `CEPRoutingCard`, `HarvestSummaryCard`, `PrincipleQuoteCard`) reflect empire's vocabulary — they're working examples, not requirements. Replace, extend, or ignore as fits your agent.
