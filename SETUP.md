# Setting up Alliance Canvas for your own Gemma (or any Ollama) agent

Alliance Canvas is opinionated but not locked. The shipped configuration runs Archie — a Gemma 4 E4B agent with a specific identity, vocabulary, and tool set. To run it for your own model, you swap the agent config, point the workspace at your own folders, and restart. Nothing in the codebase needs to change.

## Prerequisites

- macOS, Linux, or WSL2 (uses `python3.11`, `node ≥ 20`, `bash`)
- [Ollama](https://ollama.com/download) running locally on `:11434`
- An Ollama model installed (`ollama pull gemma3:4b` or your model of choice)
- Optional: a Modelfile that gives your model a stable identity (recommended)

## 30-second smoke setup (use the bundled Archie example)

```bash
git clone https://github.com/<you>/alliance-canvas.git
cd alliance-canvas
./scripts/start.sh
```

You'll see "Archie not connected" if you don't have a model named `archie:latest` in Ollama. Either:

- `ollama pull gemma3:4b && ollama cp gemma3:4b archie` to alias an existing model, or
- Skip ahead to **Run with your own model**.

## Run with your own model

### 1. Create an agent config

Copy the example file:

```bash
mkdir -p ~/.alliance-canvas/agents
cp config/agents/example-myagent.json.example ~/.alliance-canvas/agents/myagent.json
```

Edit the copy:

```json
{
  "name": "myagent",
  "display_name": "My Agent",
  "model": "gemma3:4b",
  "color": "#3B82F6",
  "avatar_emoji": "🤖",
  "connected": true,
  "machine": "local",
  "tool_allowlist": [],
  "system_prompt_extra": "",
  "handoff_matrix": {}
}
```

The `name` field must match the filename stem. The `model` field must be exactly the Ollama model tag (`ollama list` shows them).

### 2. (Optional) Give your model an identity via a Modelfile

```bash
mkdir -p ~/Desktop/workshop/modelfiles
cat > ~/Desktop/workshop/modelfiles/myagent.Modelfile <<'MODELFILE'
FROM gemma3:4b

SYSTEM """You are My Agent. You operate as a thinking partner for [your context]…
[Whatever identity you want]
"""

PARAMETER temperature 0.5
PARAMETER num_ctx 32768
MODELFILE

ollama create myagent -f ~/Desktop/workshop/modelfiles/myagent.Modelfile
```

Then in your agent config: `"model": "myagent", "modelfile": "myagent.Modelfile"`. The canvas will read the modelfile and surface its system prompt in the agent identity panel.

### 3. (Optional) Configure tools

The bundled tools at `~/Desktop/workshop/tools/*.py` are empire-flavored — `define_term`, `load_principle`, `search_vault`, `search_web`, `read_transcript`, etc. They depend on having `~/Desktop/workshop/glossary/ecosystem-glossary.json`, `~/principles-claw/`, and `~/Obsidian/` set up. **You don't need any of them.**

To start with no tools, set `"tool_allowlist": []` in your agent JSON. The agent will chat without tool access.

To wire your own tools, drop Python files into `~/Desktop/workshop/tools/` (or wherever your workspace's `folder_mounts.workshop` points) following the [Open WebUI tool format](https://docs.openwebui.com/features/plugin/tools/) — a `class Tools` with public methods, type-hinted parameters, and `:param:` docstrings. The canvas auto-discovers them.

### 4. Set your workspace folders

Edit `~/.alliance-canvas/workspaces/Default.json` (auto-created on first run from `config/workspaces/Default.json`):

```json
{
  "name": "Default",
  "color": "#10B981",
  "description": "Your space",
  "folder_mounts": {
    "workshop": "~/path/to/your/tools-and-skills",
    "principles_claw": "~/path/to/your/principles",
    "vault": "~/path/to/your/notes"
  },
  "active_skills": [],
  "active_ceps": [],
  "active_tools": [],
  "model_params": {
    "num_ctx": 32768,
    "temperature": 0.5
  },
  "default_crew": ["myagent"]
}
```

`folder_mounts` paths only matter if you're using the bundled tools or skills. For pure chat, the existing defaults are harmless.

### 5. Run

```bash
./scripts/start.sh
open http://localhost:5180
```

## Adding skills

Skills live as folders at `<workshop>/skills/<slug>/SKILL.md` with YAML frontmatter. See `~/Desktop/workshop/skills/slut-harvest/SKILL.md` for a worked example.

```markdown
---
name: my-skill
description: One-line description shown to the agent
version: 1.0.0
emoji: "📐"
---

# My Skill

Markdown body. Loaded into the agent's context when they call `load_skill('my-skill')`.
```

The canvas's `list_skills` / `load_skill` tool functions are always available to the agent (no allowlist needed for the canvas-native skill runner).

## Adding card types

Cards are visual renderers for structured agent output. The canvas ships with `SLUTCard`, `CEPRoutingCard`, `HarvestSummaryCard`, `PrincipleQuoteCard`, `FallbackCard`. To add a `WeatherCard`:

1. Create `frontend/src/lib/components/cards/WeatherCard.svelte` accepting `data: Record<string, any>` as a prop.
2. Add a branch in `frontend/src/lib/components/CardRenderer.svelte`:
   ```svelte
   {:else if card.card_type === 'WeatherCard'}<WeatherCard data={card.data} />
   ```
3. Tell the agent it exists by extending the prompt postscript in `backend/chat_engine.py:_build_system_prompt`.

The agent emits cards as fenced code blocks with language `card`:

````
```card
{"type": "card", "card": "WeatherCard", "data": {"temp_f": 68, "city": "Brooklyn"}}
```
````

Unknown card types fall back to a generic JSON dump — nothing crashes if the agent invents a card name you haven't built yet.

## Multi-agent setups

Drop more agent JSONs into `~/.alliance-canvas/agents/`. The crew sidebar reappears automatically when there's more than one connected agent. Switch between them via the sidebar; the agent identity badge in the top bar always reflects the active one.

## Troubleshooting

**"Backend boot error"** in the UI: the backend isn't running. Check `~/.alliance-canvas/logs/backend.log`.

**"ollama unreachable"** in `/api/health`: Ollama isn't running. Open the Ollama Mac app or `ollama serve` on Linux.

**Agent connects but every message stalls**: the `model` field doesn't match an installed model. `ollama list` to verify; `ollama pull <tag>` to fix.

**Tool calls never fire**: not all Ollama models support native tool-calling. Gemma 3, Gemma 4, Llama 3.1+, Qwen 2.5+, Mistral 0.3+ are known to work. Smaller models may emulate inconsistently — try a more directive prompt ("Call X with arg=Y") or use a model with stronger tool-following.

**Tool calls fire but with bad arguments**: that's the model's tool-calling layer. CEP-13: re-read the tool's `:param:` docstrings, simplify the schema, or restate the request.

**Cards never render, just JSON in the chat**: the agent isn't honoring the `card` fence convention. The system prompt postscript explains it once; not every model picks it up. You can either (a) be more directive in the user message ("Emit your answer as a SLUTCard"), or (b) accept JSON-as-text — it's still readable.
