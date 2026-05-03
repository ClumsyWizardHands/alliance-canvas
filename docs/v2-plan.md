# Alliance Canvas — v2 Build Plan

**Status:** Plan, not yet executing. Awaiting decisions on open questions before phase 0 starts.
**Drafted:** 2026-05-03
**Owner:** Alex Crowell (with Claude as build partner)

---

## Vision

Alliance Canvas v1 is a working chat surface for one local Ollama-backed agent. v2 is the move from "chat UI" to **principles-based-computing operating environment for local models** — model-agnostic among local Ollama models, opinionated about PBC.

Three commitments shape v2:

1. **Local-model-first.** Not built around Gemma 4 E4B. Built around any local Ollama model that supports tool-calling. Performance, RAM assumptions, and tool surfaces are *generic* — E4B is the smallest target, not the constraining one.
2. **Verb-native, not noun-native.** PBC is a way of *navigating memory* through actions (CEP protocols, skills, the Ralph discipline, the Mint discipline). The canvas surfaces those verbs as first-class UI primitives. Principles are not folders — they are protocols that activate when triggered.
3. **Visibility under the hood.** "What is the model thinking, what context is loaded, what verb is active, what principles SHOULD shape this turn" — all of these become legible. The canvas's distinctive contribution over Open WebUI / Cline / ChatGPT is making the cognition layer visible and editable.

What we are explicitly NOT building: cloud providers, multi-user auth, mobile companion, voice, plugin marketplace, OWUI fork.

---

## Build phases

### Phase 0 — Debt sweep (1-2 days)

| Item | Detail |
|---|---|
| Identity Stack replaces handoff matrix | Agent panel shows model + Modelfile SYSTEM block + active skills + active CEPs + tool count, with a diff against Modelfile baseline ("here's what this workspace adds on top"). Handoff matrix removed from JSON schema entirely. |
| Date bug fix | `LedgerPanel.svelte` heuristic: if `ts < 2_000_000_000`, multiply by 1000 before `new Date()`. Same fix anywhere else timestamps are rendered. |
| Chat density tightening | Drop the colored left-border accent; tighten bubble padding `py-2.5` → `py-1.5`; cap chat column at `max-w-2xl`; reduce per-message vertical gap. |
| Favicon | Real favicon, not the data-URI placeholder. |

**Ships as:** v0.2.0 push to GitHub.

---

### Phase 1 — Multi-page architecture (2-3 days)

Promote the side panels to dedicated routes. SvelteKit filesystem routing makes this nearly free.

```
/                  → chat (home)
/sessions          → session browser (date / workspace / search)
/sessions/[id]     → one session's full thread tree
/vault             → searchable SLUT graph
/principles        → principles browser (kernel / rgt / applied / protocols, stack-tagged)
/principles/[slug] → one principle's body + engagements
/skills            → skills browser
/skills/[slug]     → one skill's body + activation history
/ledger            → full ledger w/ filters
/agent             → identity stack (live editable in Phase 6)
/settings          → workspace + tool valve config
```

The right-side `SidePanel` component stays for quick contextual peeks during chat, but the *full views* move to pages. Top-bar buttons start linking to routes instead of toggling panels.

---

### Phase 2 — Threading + Sessions (3-4 days)

**Data model.**
- `messages` table gains `thread_id` and `parent_message_id` columns.
- New `threads` table: `id`, `conversation_id`, `parent_message_id`, `title`, `started_by_verb`, `pinned_anchors_json`, `created_at`.
- New `sessions` table: `id`, `started_at`, `ended_at`, `workspace`, `summary`, `verb_timeline_json`.
- `conversations.session_id` foreign-key column.

**Backend.**
- `POST /api/threads` (spawn from message) — creates a thread with a curated context window seeded from the parent message + selected SLUTs.
- `GET /api/sessions` / `GET /api/sessions/:id`.
- Session lifecycle: auto-create on first turn each calendar day; explicit close via UI; explicit "start new session" button.

**Frontend.**
- "→ thread" button on hover for any message.
- Threads display as collapsible sub-trees inline in the chat stream, with breadcrumbs to the parent message.
- `/sessions` browser: calendar + list view, filter by workspace, search by content / verb / SLUT slug.
- `/sessions/[id]`: full tree of conversations + threads + verbs + cards emitted, scrollable timeline.

---

### Phase 3 — Sub-agents + Thinking trace + Ralph + Pass schema (4-5 days)

**Pass schema** — formal protocol for parent → sub-agent handoffs. Sketched:

```json
{
  "version": "1.0",
  "from": "archie",
  "to": "subagent.skeptic",
  "intent": "ralph",
  "claim": "...",
  "anchors": [
    {"type": "modelfile", "ref": "archie"},
    {"type": "cep",       "ref": "cep-13"},
    {"type": "principle", "ref": "pc-07"}
  ],
  "constraints": {
    "clean_slate": true,
    "tools_allowed": [],
    "max_tokens": 1024
  },
  "expected_return": {
    "shape": "ralph_response_v1",
    "fields": ["agreement", "alternative_view", "confidence", "principle_refs"]
  }
}
```

Return shape symmetrical:

```json
{
  "version": "1.0",
  "for": "<turn_id>",
  "from": "subagent.skeptic",
  "agreement": "partial",
  "alternative_view": "...",
  "confidence": 0.7,
  "principle_refs": ["pc-07"],
  "thinking_trace": "...",
  "spent_tokens": 412
}
```

Both pass and return logged to the session ledger as verb-shaped entries.

**Backend.**
- `backend/subagent.py` — orchestrates parallel Ollama calls with clean-slate context; serializes execution if RAM is constrained (configurable). Each sub-agent gets its own pass + return.
- Stream `message.thinking` field from Ollama's chat API as a separate WS event channel; available now in Gemma 3+, Qwen, etc.

**Frontend.**
- Collapsible "← thinking" rail next to each assistant message.
- Sub-agent lanes: when N sub-agents run, the chat stream forks into N parallel columns for the duration; merges back when they all return.
- **Ralph button**: hover any sentence in an assistant message → "ralph this." Spawns 2-3 sub-agents (skeptic / alternative-source / principle-fitness). Returns rendered as a comparison panel: agreement summary on top, **disagreement preserved on the bottom as separate signal** (per the kernel "preserve disagreement" rule).

---

### Phase 4 — Memory layer (3-4 days)

**Storage.** SQLite + `sqlite-vec` extension. One database file (`db.sqlite`), one extra table:

```sql
CREATE TABLE memories (
  id          INTEGER PRIMARY KEY,
  content     TEXT NOT NULL,
  tags        TEXT,
  source_id   TEXT,           -- e.g. "message:123" or "session:45"
  embedding   BLOB,           -- mxbai-embed-large via sqlite-vec
  created_at  INTEGER
);
```

**Tools (canvas-native).**
- `remember(content, tags?)` — embed and store.
- `recall(query, k=5)` — semantic search; returns top-k.
- `forget(id)` — delete.

**UI.**
- Inline memory-recall chip in the chat: "↺ recalled 3 from memory" with hover preview.
- `/memory` page (or sub-route under `/sessions`?) showing all memories with tag filters and a search box.
- Memory ops appear in the session ledger as verb entries (`remember`, `recall`).

---

### Phase 4.5 — Skill audit + port (cross-cutting, ~1-2 days)

Survey existing skills across Alex's environment and port the ones that are model-agnostic:

- `~/.claude/plugins/anthropic-skills/` — verb-shaped skills (`request`, `pass`, `mvp`, `slut-harvest`, `consolidate-memory`, `setup-cowork`, `schedule`)
- `~/atlas/.claude/skills/` — Atlas's plugin skills (`pbc-core`, `pbc-coordination`, `pbc-visual` packs)
- Other Claude Code skills that don't require Anthropic API specifically

Classify each: **port** (works as a text-only operational protocol any local model can follow), **adapt** (mostly portable with small tool-substitutions), **skip** (requires Anthropic API features like extended thinking, tools we don't have, or skills that are just orchestration glue).

Ported skills land at `~/Desktop/workshop/skills/<slug>/SKILL.md` in AgentSkills format and become toggleable in workspaces.

---

### Phase 5 — Code execution (3-4 days)

**Architecture.** Two distinct tools, distinct UI:

- `bash(command: str)` — runs in `~/.alliance-canvas/sandbox/<turn_id>/`, separate cwd per turn, cleaned up on session end. Stdout + stderr returned together.
- `python(code: str)` — runs in a fresh subprocess REPL with stdlib + a small allowed-import set (`math`, `json`, `re`, `pathlib`, `datetime`, `csv`). Stdout returned.

**Guardrails (mandatory, not optional).**
- Approval gate: first 3 calls per session require user click. Pattern-matched dangerous ops always require approval forever (`rm`, `mv`, `>`, `curl`, `wget`, `git push`, `chmod`, `chown`, `sudo`).
- Sandbox cwd never escapes via `..` — sanitize.
- Hard wall-clock timeout: 30s default, configurable per workspace.
- Network access: bash inherits host network (acceptable in v1); python sandboxed with no socket access.

**UI.**
- Bash chips: terminal icon, monospace dark output, exit-code badge.
- Python chips: snake icon, syntax-highlighted code, output below.
- Both share the same approval gate UX: a yellow chip with "approve / deny / approve all this turn" buttons.
- "Rerun this" button on each chip.

This is the *capability* play. Most local models will mis-call bash; that's OK — the gate makes it a learning surface, not a destruction surface.

---

### Phase 6 — Time-travel + Live Modelfile editor (2-3 days)

**Time-travel.** Every message has a "branch from here" action (already enabled by Phase 2's threading data model — branching IS spawning a thread, just with a different conceptual framing). UI shows the parent-conversation tree with branch points marked.

**Live Modelfile editor.** `/agent` becomes editable. The Modelfile SYSTEM block is rendered as a textarea. Save flow:

1. Show diff vs. current.
2. Run `ollama create <agent_name> -f <tmp_modelfile>` in background.
3. On success: hot-swap; show "Archie reloaded."
4. On failure: roll back, show stderr in the panel.

5-15s save latency on M4 Pro — UI shows progress, doesn't just spin. This makes Archie's identity sculptable from inside the canvas instead of via SSH.

---

### Phase 7 — Verb-based interaction layer (5-7 days, REVISED)

**Reframed:** Originally drafted as "principles as primary navigation" (noun-based). Push from Alex: PBC is verb-native. The right move is to surface and scaffold the *actions* PBC thinks in.

**The verbs.** Hand-curated initial palette, drawn from CEPs + skills + ecosystem glossary:

| Verb | What it does | Backed by |
|---|---|---|
| `scan` | Run CEP-routing-table scan against the current draft message | CEP-00 / scanning skill |
| `load` | Load a principle, CEP, or skill into the next turn | `load_principle`, `load_skill` |
| `compose` | Run multiple CEPs in index order | "Composition" rule in CEP-NAV |
| `ralph` | Triangulate a claim via 2-3 sub-agents | Modelfile rule + CEP-11 |
| `mint` | Start a SLUT draft with CEP-14 loaded | CEP-14 |
| `harvest` | Run the slut-harvest skill end-to-end on selected material | slut-harvest skill |
| `audit` | Run CEP-12 self-audit on the active conversation/session | CEP-12 |
| `investigate` | Run CEP-13 ceiling investigation when blocked | CEP-13 |
| `slipknot` | Find existing SLUTs in vault to connect to draft | search_vault tool |
| `surface` | Write something to the ledger | write_ledger |
| `anchor` | Add a backward/present/forward anchor to current draft | CEP-anchors pattern |
| `sit-with` | Defer surfacing; mark for later contemplation | CEP-00 contemplation |
| `defend` | Articulate the offensive-resilience move for a claim | Triple Helix rule |

**Three new UI surfaces:**

1. **Verb palette.** Floating action bar above the composer. Click a verb → it modifies the next turn's behavior (loads relevant CEP, opens sub-agent pane, starts a thread tagged with the verb). Keyboard shortcuts: `cmd+r` ralph, `cmd+m` mint, `cmd+s` scan, etc.

2. **Live CEP scan as you type.** A small worker runs a quick local pass over the draft message against the CEP routing table (titles + triggers). Matches surface as inline chips: "CEP-04 (transcripts) might apply — auto-load?" Click to load; click X to dismiss. **Decision needed (open question 2):** aggressive auto-load, polite suggest-and-confirm, or just-surface-as-chip.

3. **Verb-tagged threads & verb-timeline sessions.** Every thread carries a `started_by_verb` tag. The session view becomes a verb timeline: "Tuesday: harvest → ralph → mint → mint → audit." This makes work legible as PBC actions instead of as messages.

**Send button becomes verb-aware.** "Send (CEP-04 + slut-harvest active)" so you see what shape Archie's about to be in *before* you send. If no verbs/CEPs active, just "Send."

**Toggle for v2.** This whole layer is opt-in via a "PBC mode" toggle in `/settings`. Default off (chat-first nav for new users); single-click ON for empire users. Promote to default in v3 once classifier and palette have proven out.

---

## Cross-cutting concerns

### Risks (logged + mitigations)

- **RAM with sub-agents.** Acknowledged but not blocking. Configurable serialize-vs-parallelize per workspace. Not E4B-specific — same logic for any local model.
- **Code-exec hallucinations.** Approval gate mandatory. Pattern blocklist for destructive ops always-on. Not relying on E4B's good judgment.
- **`ollama create` latency.** UI shows progress, doesn't lie about speed.
- **Verb classifier accuracy** (Phase 7 live-scan). Manual override + "this is also a `mint`" affordance. Errors visible, not hidden.
- **Card parser × sub-agent lanes.** Each lane needs its own card stream. Land sub-agents simply first; revisit nested cards if/when needed.
- **Open WebUI tool format.** Currently we load OWUI-shaped tools as-is. Decision deferred (open question 9): evolve to a richer canvas-native format or stay portable.

### Open questions (need Alex's input)

1. **Verb palette scope.** Hand-curated list (faster) or auto-derive from CEPs + skills + ecosystem glossary (more empire-honest)? My lean: hand-curated v2, auto-derive v3.
2. **CEP auto-loading aggressiveness.** (a) auto-load on match, (b) suggest + confirm, (c) just-surface-as-chip. Three different UX implications. My lean: (b) for v2.
3. **Pass schema review.** Sketched in Phase 3. Should I formalize as `shared/schemas/pass.schema.json` or do you have prior pass-schema work I should adapt?
4. **Skill audit scope.** Audit-all (~half day) / port-only-the-portable (~1 day) / defer entirely. My lean: audit-all → classify → port-the-portable.
5. **Bash + Python UI.** Distinct chips with distinct icons (terminal vs python), same approval gate? My lean: yes, distinct.
6. **Identity Stack rendering.** Panel inspector / live "what shape is Archie in" viz / diff view ("Modelfile baseline + workspace adds"). My lean: diff view.
7. **PBC mode toggle scope.** Minimal (palette + chips), Medium (above + verb-tagged threads), Maximal (above + verb dashboard as home). My lean: ship minimal, escalate.
8. **Sessions vs threads.** Sessions auto-end (idle / EOD) or always manual? My lean: auto-end on 4-hour idle; explicit "start new session" button always available.
9. **Tool format evolution.** Stay OWUI-compatible (portable) or define canvas-native richer format (CEP refs, output card types, pass schema)? My lean: stay OWUI-compatible v2; canvas-native superset declared in optional metadata block.
10. **Plan storage location** ✓ resolved: `/docs/v2-plan.md` in repo (this file).

### Decisions logged (already answered)

- ✓ Memory store: SQLite + sqlite-vec (not ChromaDB)
- ✓ Sub-agent context: clean slate by default; "with context" available as a flag for explicit composition
- ✓ Code execution: build it (bash + Python both), even though E4B isn't a code-exec model — other local models will use it
- ✓ PBC mode: opt-in toggle (Phase 7), not default
- ✓ Build for any local Ollama model with tool-calling, not E4B specifically
- ✓ Verb-native, not noun-native (Phase 7 reframed)
- ✓ Need a manual override on the live CEP scanner (Phase 7)

---

## Build order

```
0  ─→  1  ─→  2 ─┬─→  3 (sub-agents + ralph + thinking + pass)
                  │
                  ├─→  4 (memory)        ← parallel-able after 2
                  │
                  ├─→  4.5 (skill audit) ← parallel-able anytime
                  │
                  ├─→  5 (code exec)     ← independent
                  │
                  └─→  6 (time-travel + Modelfile editor)
                                                ↓
                                                7 (verb layer)
```

Phases 0-2 are foundational. After 2, phases 3-6 are mostly parallel-able. Phase 7 sits last because it depends on threads, sessions, sub-agents, and the skill set being stable.

**Total: ~25-30 days focused work** = 4-6 weeks at sustainable pace.

Ship each phase as a discrete release (`v0.2.0` after 0, `v0.3.0` after 1, etc.). Each is independently demoable.

---

## What "first turn of the build" looks like

Once phase 0 starts, the very first commits are:

1. `backend/agents.py` — drop `handoff_matrix` from the schema; emit warning if present in legacy JSONs.
2. `frontend/src/lib/components/SidePanel.svelte` — replace agent panel's handoff-matrix block with Identity Stack diff view.
3. `frontend/src/lib/components/SidePanel.svelte` — date-fix heuristic in `fmtTs`.
4. `frontend/src/lib/components/MessageBubble.svelte` — chat density tightening.
5. `frontend/static/favicon.svg` — real favicon.
6. Tag and push as `v0.2.0`.

That's it. Clean slate before threading rewires everything.
