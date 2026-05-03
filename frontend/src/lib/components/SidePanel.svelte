<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../api';
  import { ui, getActiveAgent } from '../stores.svelte';
  import Markdown from './Markdown.svelte';

  let ledger = $state<any[]>([]);
  let ledgerErr = $state<string | null>(null);
  let skills = $state<any[]>([]);
  let activeSkillBody = $state<string | null>(null);
  let activeSkillSlug = $state<string | null>(null);
  let principles = $state<any[]>([]);
  let activePrinciple = $state<{ slug: string; stack: string; body: string } | null>(null);

  async function loadLedger() {
    try {
      const r = await api.ledger(20);
      ledger = r.entries;
      ledgerErr = null;
    } catch (e: any) {
      ledgerErr = e.message;
    }
  }

  async function loadSkills() {
    const r = await api.skills(ui.activeWorkspace);
    skills = r.skills;
  }

  async function loadSkillBody(slug: string) {
    activeSkillSlug = slug;
    const s = await api.skill(slug, ui.activeWorkspace);
    activeSkillBody = s.body ?? null;
  }

  async function loadPrinciples() {
    const r = await api.principles(ui.activeWorkspace);
    principles = r.principles;
  }

  async function loadPrincipleBody(slug: string) {
    activePrinciple = await api.principle(slug, ui.activeWorkspace);
  }

  $effect(() => {
    if (ui.rightPanel === 'ledger') loadLedger();
    if (ui.rightPanel === 'skills') {
      loadSkills();
      activeSkillBody = null;
      activeSkillSlug = null;
    }
    if (ui.rightPanel === 'principles') {
      loadPrinciples();
      activePrinciple = null;
    }
  });

  function close() {
    ui.rightPanel = null;
    activeSkillBody = null;
    activeSkillSlug = null;
    activePrinciple = null;
  }

  function fmtTs(ts: any): string {
    if (!ts) return '';
    if (typeof ts === 'number') return new Date(ts).toLocaleString();
    return String(ts);
  }
</script>

{#if ui.rightPanel}
  <aside class="flex h-full w-96 shrink-0 flex-col border-l border-zinc-900 bg-zinc-950">
    <header class="flex items-center justify-between border-b border-zinc-900 px-3 py-2">
      <h3 class="text-xs font-semibold uppercase tracking-wider text-zinc-400">
        {#if ui.rightPanel === 'ledger'}Memory ledger
        {:else if ui.rightPanel === 'skills'}Skills
        {:else if ui.rightPanel === 'principles'}Principles
        {:else if ui.rightPanel === 'agent'}Agent identity
        {/if}
      </h3>
      <button class="rounded px-2 py-0.5 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200" onclick={close}>×</button>
    </header>

    <div class="flex-1 overflow-y-auto p-3 text-sm">
      {#if ui.rightPanel === 'ledger'}
        {#if ledgerErr}
          <p class="text-rose-400">{ledgerErr}</p>
        {:else if !ledger.length}
          <p class="text-zinc-500">Ledger empty or not yet loaded.</p>
        {:else}
          <ul class="flex flex-col gap-2">
            {#each ledger.slice().reverse() as entry}
              <li class="rounded border border-zinc-900 bg-zinc-900/40 p-2">
                <div class="flex items-baseline gap-2 text-[11px] text-zinc-500">
                  <span class="font-mono">{fmtTs(entry.timestamp ?? entry.ts ?? entry.time)}</span>
                  {#if entry.agent}<span>· {entry.agent}</span>{/if}
                  {#if entry.kind || entry.type}<span>· {entry.kind ?? entry.type}</span>{/if}
                </div>
                <div class="mt-1 text-xs text-zinc-200">
                  {entry.summary ?? entry.message ?? entry.title ?? entry.content ?? JSON.stringify(entry).slice(0, 200)}
                </div>
              </li>
            {/each}
          </ul>
        {/if}

      {:else if ui.rightPanel === 'skills'}
        {#if activeSkillBody}
          <button class="mb-2 text-xs text-zinc-400 hover:text-zinc-200" onclick={() => { activeSkillBody = null; activeSkillSlug = null; }}>← all skills</button>
          <div class="text-xs font-mono text-zinc-500">{activeSkillSlug}</div>
          <Markdown text={activeSkillBody} />
        {:else if !skills.length}
          <p class="text-zinc-500">No skills active in this workspace.</p>
        {:else}
          <ul class="flex flex-col gap-1.5">
            {#each skills as s}
              <li>
                <button
                  class="w-full rounded border border-zinc-900 bg-zinc-900/40 p-2 text-left hover:bg-zinc-900"
                  onclick={() => loadSkillBody(s.slug)}
                >
                  <div class="flex items-baseline gap-2">
                    {#if s.emoji}<span>{s.emoji}</span>{/if}
                    <span class="font-mono text-xs text-zinc-200">{s.slug}</span>
                    {#if s.is_folder_format}<span class="rounded bg-zinc-800 px-1 text-[9px] uppercase tracking-wider text-zinc-400">folder</span>
                    {:else}<span class="rounded bg-amber-900/50 px-1 text-[9px] uppercase tracking-wider text-amber-300">flat</span>{/if}
                  </div>
                  <div class="mt-1 text-xs text-zinc-400">{s.description}</div>
                </button>
              </li>
            {/each}
          </ul>
        {/if}

      {:else if ui.rightPanel === 'principles'}
        {#if activePrinciple}
          <button class="mb-2 text-xs text-zinc-400 hover:text-zinc-200" onclick={() => (activePrinciple = null)}>← all principles</button>
          <div class="flex items-baseline gap-2">
            <span class="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] uppercase text-zinc-300">{activePrinciple.stack}</span>
            <span class="font-mono text-xs text-zinc-400">{activePrinciple.slug}</span>
          </div>
          <div class="mt-2"><Markdown text={activePrinciple.body} /></div>
        {:else if !principles.length}
          <p class="text-zinc-500">No principles indexed for this workspace.</p>
        {:else}
          {@const grouped = principles.reduce((acc, p) => { (acc[p.stack] ||= []).push(p); return acc; }, {} as Record<string, any[]>)}
          <div class="flex flex-col gap-3">
            {#each Object.keys(grouped) as stack}
              <div>
                <div class="mb-1 text-[10px] uppercase tracking-wider text-zinc-500">{stack}</div>
                <ul class="flex flex-col gap-1">
                  {#each grouped[stack] as p}
                    <li>
                      <button
                        class="block w-full rounded px-2 py-1 text-left hover:bg-zinc-900"
                        onclick={() => loadPrincipleBody(p.slug)}
                      >
                        <span class="font-mono text-xs text-zinc-300">{p.slug}</span>
                        <span class="block text-[11px] text-zinc-500">{p.title}</span>
                      </button>
                    </li>
                  {/each}
                </ul>
              </div>
            {/each}
          </div>
        {/if}

      {:else if ui.rightPanel === 'agent'}
        {@const a = getActiveAgent()}
        {#if a}
          <div class="flex items-baseline gap-2">
            <span class="text-2xl">{a.avatar_emoji ?? '·'}</span>
            <span class="text-base font-semibold" style="color: {a.color ?? '#10B981'}">{a.display_name ?? a.name}</span>
          </div>
          <div class="mt-1 text-xs text-zinc-500">model: <span class="font-mono">{a.model}</span></div>
          <div class="text-xs text-zinc-500">machine: <span class="font-mono">{a.machine}</span></div>
          {#if a.handoff_matrix && Object.keys(a.handoff_matrix).length}
            <div class="mt-3">
              <div class="mb-1 text-[10px] uppercase tracking-wider text-zinc-500">Handoff matrix</div>
              <ul class="grid grid-cols-1 gap-0.5 text-xs">
                {#each Object.entries(a.handoff_matrix) as [trigger, target]}
                  <li class="flex justify-between gap-2 rounded px-2 py-0.5 hover:bg-zinc-900">
                    <span class="text-zinc-400">{trigger}</span>
                    <span class="font-mono text-zinc-300">→ {target}</span>
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
          {#if a._modelfile_text}
            <details class="mt-3">
              <summary class="cursor-pointer text-xs text-zinc-400 hover:text-zinc-200">Modelfile</summary>
              <pre class="mt-1 whitespace-pre-wrap rounded bg-zinc-900 p-2 text-[11px] text-zinc-300">{a._modelfile_text}</pre>
            </details>
          {/if}
        {/if}
      {/if}
    </div>
  </aside>
{/if}
