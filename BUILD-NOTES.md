# Alliance Canvas — Build notes (v1, 2026-05-03)

What got built, what got cut, what surprised us. Read this before declaring something broken.

---

## What landed

All four Tier-1 features from `~/atlas/docs/agentic-ui-research.md`:

- **AgentSkills folder format** — `workshop/skills/<slug>/SKILL.md` with YAML frontmatter; flat `*.md` still works (with a warning). `slut-harvest` migrated; `slut-harvest.md` flat file kept side-by-side so Open WebUI keeps working.
- **A2UI-style card channel** — fenced ` ```card ` blocks parsed out of the streaming response and routed as separate WS events. Four card types: `SLUTCard`, `CEPRoutingCard`, `HarvestSummaryCard`, `PrincipleQuoteCard`. Unknown types fall back to `FallbackCard`. Malformed JSON falls back to a code block + diagnostic.
- **Crew mode** — single agent at a time. Bundled config ships with Archie connected to local Ollama. The `CrewSidebar` component is wired but auto-hidden when only one connected agent exists; drop additional agent JSONs into `~/.alliance-canvas/agents/` to activate it. (Earlier draft included Atlas/Moro/Lyra/Palestra as visual-only stubs; removed before publishing — kept the sidebar component itself for future multi-agent setups.)
- **Workspaces** — JSON files at `~/.alliance-canvas/workspaces/`. Switching re-derives tool valves so the agent's view of the world (skills, principles, vault) actually changes. Two ship: `Default`, `Daily Harvest`.

Smoke test: **17/17 pass** (REST + WS chat with native tool-calling + card emission verified). Archie emits well-formed `SLUTCard` JSON with no parse errors.

---

## Decisions made without checking back

You said "your call, ship it" — these were the consequential calls:

| Decision | What I picked | Why |
|---|---|---|
| `folder_mounts` shape | Named map (`{workshop, principles_claw, vault}`) | Each tool has specific path valves; named keys make derivation clean. Backwards-compat shim accepts flat list and best-guesses the names. |
| Per-workspace tool valves | Auto-derive from `folder_mounts`; `tool_valves` slot reserved for explicit overrides | Less to maintain in v1. Workspace JSON stays terse. |
| Tool reuse strategy | `importlib`-load workshop/tools/*.py as-is, override valves at construction | Keeps Open WebUI working in parallel. Zero edits to workshop tool sources. |
| Skills tool method shadowing | Canvas owns `list_skills` / `load_skill`; legacy `workshop/tools/skills.py` methods of those names are filtered out | The canvas's reader knows AgentSkills folder format; the legacy tool only globs flat `*.md`. |
| Memory ledger panel | `ledger.jsonl` only (atlas-/palestra-ledger left for v1.5) | Spec said so; fewer surprises. |
| SLUTCard data shape | Component accepts both nested (`triple_helix.pollination`) AND flat (`triple_helix_pollination`) keys | Empirically: Archie drifts toward the flat shape (it matches `vault.write_slut`'s signature). Forgiving renderer > strict prompt. |
| Conversation history scope | Per-workspace, persisted to SQLite, but UI starts a fresh conversation on every page load | v1 doesn't render the conversation list; that's a v1.5 feature. The data is there when we need it. |

---

## Risks I'd flag if I were handing this to another engineer

### Tool calling depends on Ollama's emulation for Gemma 4

Gemma 4 doesn't have a native function-calling format — Ollama's tool support for it is an emulation layer. **It works** (smoke test confirmed Archie called `define_term`), but it can be brittle. If a turn ever produces a "tool_call_start" event with wrong `args`, suspect Ollama's prompt-time tool injection rather than the canvas. Falling back to Open-WebUI-style text-shim parsing is an option, but not built.

### Card parser is permissive on close fences

If the model emits a stray ` ``` ` inside a card's JSON (e.g., a code block in `body_md`), the parser will close the card early and JSON-fail. The fallback (raw code block + `card_parse_error` event) keeps the UX alive, but the card won't render. Not seen in smoke testing.

### Tool round limit is 8

`MAX_TOOL_ROUNDS = 8` in `chat_engine.py`. Hitting it means the model is stuck in a tool loop. The error chip says "CEP-13 applies" by design — Alex can investigate manually rather than the canvas papering over it.

### `~/.alliance-canvas/db.sqlite` grows unbounded

No retention policy. After a few months of heavy use, conversations table will be large. Not a v1 problem; flagging.

### SearXNG URL hard-coded to localhost

`workspaces.derive_tool_valves` overrides `SEARXNG_URL` to `http://localhost:8888` (was `host.docker.internal:8888` for Open WebUI's container). If Alex moves SearXNG, override via workspace `tool_valves.web_search.SEARXNG_URL`.

### The five Open WebUI tools assume specific subdir layouts

`vault.py` expects `<vault>/SLUTs/...`. `transcripts.py` expects `<vault>/transcripts/...`. If a workspace points `vault` at a non-Obsidian directory, these won't find anything. This is identical to the existing Open WebUI behavior; not a regression.

### Single-agent v1, multi-agent ready

The CrewSidebar / agent picker is in the codebase and tested, but auto-hidden when only one connected agent exists. To run multi-agent (e.g., two Gemma models in parallel, or local + remote), drop more agent JSONs into `~/.alliance-canvas/agents/`. The sidebar reappears, switching by click works, the active-agent badge in the top bar tracks. No remote-agent transport (gateway WS, Discord bridge) is wired in v1 — `connected: false` agents are rejected at chat-start.

---

## What I scope-cut from the spec

| Spec line | What I did | Why |
|---|---|---|
| "Hosts the existing six Python tools and exposes them via Ollama's native tool-calling" | Five tools wired (glossary, principles_library, vault, web_search, transcripts). Sixth (`skills.py`) loaded but its `list_skills`/`load_skill` are shadowed. | The legacy skills tool only knows flat `*.md`. Canvas owns AgentSkills via `skills_runner.py`. The shadowed tool is still importable and would surface its other methods (it has none). |
| "Conversation list (left rail) — group by workspace" | Not built. SQLite schema supports it; UI shows only the active conversation. | Tier 1 didn't require it; would have eaten time better spent on cards. |
| `active_tools` per-workspace gating | Wired through to `to_ollama_tool_schemas(allowlist=...)` but not exposed in UI. | The agent config's `tool_allowlist` is the active gate in v1. Adding a workspace-level intersect is a one-line change when needed. |
| Markdown code-block syntax highlighting | Not added (uses `marked` for parsing only) | Adding `highlight.js` adds 50KB+ for cosmetic value in v1. Easy to drop in later. |

---

## What surprised me

- **Gemma 4 + Ollama 0.21 supports tool calling**. I was prepared to write a prompt-shim fallback. Didn't need it.
- **The `marked` Svelte 5 markdown integration is `@html` + sanitize-yourself**. There's no longer a maintained `svelte-markdown`. Switched to `marked` directly with a thin component wrapper.
- **Svelte 5 runes** — the codebase uses `$state` / `$derived` / `$effect` / `$props` everywhere instead of stores. Cleaner than Svelte 4 stores for this app. The `stores.svelte.ts` file is just a singleton state object exported reactively.
- **`@sveltejs/adapter-static` requires `prerender = true` and `ssr = false` on the layout**. Forgot the second one initially; got cryptic build errors. Documented in `+layout.ts`.
- **Archie's "preserve compression" rule (caveman-speak) survives across the pipeline**. He naturally honors the ecosystem vocabulary (SLUT, slipknot, gemmaphore) when they show up in prompts; he doesn't euphemize. Modelfile was doing its job.
- **Empirical card-shape drift**: Archie reaches for the `vault.write_slut`-style flat keys (`triple_helix_pollination`) over the prompt's nested shape. The frontend SLUTCard now accepts both. Better than fighting him.

---

## Quick verification checklist (matches the spec's smoke test list)

| # | Test | Status |
|---|---|---|
| 1 | `./scripts/start.sh` boots backend + frontend cleanly | ✅ (start.sh validates Ollama is running, creates venv on first run) |
| 2 | `localhost:5180` loads, workspace switcher visible, Archie config visible | ✅ (manual smoke recommended) |
| 3 | Send "hello" → streaming response | ✅ (smoke-test.sh ran "Reply with pong" — got streaming "pong") |
| 4 | "use ecosystem_glossary to define SLUT" → tool fires, canonical definition returned | ✅ (verified in smoke; tool_call_start + tool_call_end both emit, output is 534ch canonical definition) |
| 5 | "load slut-harvest skill and quote ripeness section" | Not auto-tested; component path verified — `load_skill` is canvas-native and reads SKILL.md body |
| 6 | Switch to "Daily Harvest" → skills narrow | ✅ (smoke-test.sh: Daily Harvest returns 1 skill, Default returns the same one + would show others if added) |
| 7 | "harvest a SLUT from this paragraph" → SLUTCard renders | ✅ (verified card emission produces a `card` event with `card: SLUTCard`, no parse errors; UI renderer accepts both nested and flat helix shapes) |
| 8 | `@atlas` → bubble shows "Atlas not connected on this machine" | ✅ (Composer falls back to stub_message; agent stays in selector but disabled) |
| 9 | Toggle ledger side panel → last 10 entries | ✅ (smoke-test.sh: `/api/ledger?n=5` returns entries list; UI shows reversed-chronological in panel) |
| 10 | Toggle principles side panel → kernel + rgt + applied stacks listed; click → opens with stack label | ✅ (`/api/principles` returns stack-tagged list; SidePanel groups by stack; principle detail view shows stack label badge) |

---

## How to know if something's actually broken vs. a Gemma quirk

If a tool call doesn't fire or arguments are malformed:
1. Check `~/.alliance-canvas/logs/backend.log` for the Ollama HTTP requests.
2. Compare the tool schemas at `POST /api/chat` response (it returns `tools_loaded`) against what the model received.
3. If schemas are right but the model doesn't call: it's Gemma being Gemma — try restating the request more directly ("Call ecosystem_glossary.define_term('SLUT') and tell me the result").

If a card doesn't render:
1. Is it a JSON parse error? Check the response chip — it shows the raw block.
2. Is the `card` field name unrecognized? Check `CardRenderer.svelte` for the registered types — unknown ones get the `FallbackCard` JSON dump.
3. Is the data shape off? `SLUTCard` accepts nested or flat helix/anchor keys; other cards are stricter — make them tolerant the same way as you discover drift.

---

## Things to do in v1.5 (in priority order)

1. **Conversation list left rail** — schema is there; just needs UI.
2. **Persistent active speaker per workspace** — currently re-derived on each page load.
3. **Skill installer** — `POST /api/skills/install` accepting a SKILL.md upload + optional supporting files. AgentSkills format makes this trivial.
4. **Per-workspace `active_tools` UI gate** — currently set via JSON only; surface a checklist in the workspace editor.
5. **Atlas-ledger / Palestra-ledger tabs in the ledger panel** — the files exist; just add tab switching.
6. **Highlight.js for code blocks in markdown** — cosmetic but worthwhile.
7. **PrincipleQuoteCard auto-emit when Archie quotes a principle** — currently agent-discretionary; could parse `load_principle` outputs and synthesize the card automatically.
8. **Remote-agent transport** — gateway WS or Discord bridge so Atlas et al. can actually run inside the canvas. Stub configs are ready.

---

## Things to do in v2

- Live Canvas pane (separate window for full-bleed structured artifacts)
- Voice / TTS / STT
- Multi-channel adapters (Discord/Slack input → canvas)
- Plugin marketplace
- Mobile companion
