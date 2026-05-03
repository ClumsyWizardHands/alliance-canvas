<script lang="ts">
  import { ui, getActiveAgent } from '../stores.svelte';
  import type { Agent } from '../types';

  function setActive(a: Agent) {
    if (!a.connected) return;
    ui.activeAgent = a.name;
  }

  function showInfo() {
    ui.rightPanel = 'agent';
  }
</script>

<aside class="flex h-full w-60 shrink-0 flex-col border-r border-zinc-900 bg-zinc-950">
  <div class="flex items-center justify-between border-b border-zinc-900 px-3 py-2">
    <h3 class="text-xs font-semibold uppercase tracking-wider text-zinc-400">Crew</h3>
    <button class="text-xs text-zinc-500 hover:text-zinc-200" onclick={showInfo}>
      identity
    </button>
  </div>
  <ul class="flex-1 overflow-y-auto p-1">
    {#each ui.agents as a}
      <li>
        <button
          class={`flex w-full items-start gap-2 rounded-md px-2.5 py-2 text-left text-sm
            ${ui.activeAgent === a.name ? 'bg-zinc-900' : 'hover:bg-zinc-900/60'}
            ${!a.connected ? 'opacity-50 cursor-not-allowed' : ''}`}
          onclick={() => setActive(a)}
          disabled={!a.connected}
          title={a.connected ? `Talk to ${a.display_name}` : (a.stub_message ?? 'Not connected')}
        >
          <span class="mt-0.5 shrink-0">{a.avatar_emoji ?? '·'}</span>
          <span class="flex-1 min-w-0">
            <span class="flex items-center gap-1.5">
              <span class="font-medium" style="color: {a.connected ? (a.color ?? '#10B981') : '#71717a'}">
                {a.display_name ?? a.name}
              </span>
              {#if !a.connected}
                <span class="rounded bg-zinc-900 px-1 py-0.5 text-[9px] uppercase tracking-wider text-zinc-500">
                  stub
                </span>
              {/if}
            </span>
            <span class="block text-[11px] text-zinc-500">
              {a.machine ?? ''}
            </span>
          </span>
          {#if ui.activeAgent === a.name && a.connected}
            <span class="shrink-0 text-emerald-400">●</span>
          {/if}
        </button>
      </li>
    {/each}
  </ul>
  <div class="border-t border-zinc-900 px-3 py-2 text-[11px] text-zinc-500">
    @ mention to switch · stubs route nowhere in v1
  </div>
</aside>
