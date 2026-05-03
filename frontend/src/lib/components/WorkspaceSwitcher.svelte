<script lang="ts">
  import { ui } from '../stores.svelte';

  let open = $state(false);

  function pick(name: string) {
    ui.activeWorkspace = name;
    ui.conversationId = null;
    ui.messages = [];
    open = false;
  }

  const active = $derived(ui.workspaces.find((w) => w.name === ui.activeWorkspace));
</script>

<div class="relative">
  <button
    class="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-sm hover:bg-zinc-800"
    onclick={() => (open = !open)}
  >
    {#if active}
      <span class="h-2.5 w-2.5 rounded-full" style="background: {active.color ?? '#10B981'}"></span>
      <span class="font-medium">{active.name}</span>
    {:else}
      <span class="text-zinc-500">No workspace</span>
    {/if}
    <span class="text-zinc-500">▾</span>
  </button>

  {#if open}
    <div class="absolute left-0 top-full z-30 mt-1 w-72 rounded-lg border border-zinc-800 bg-zinc-900 p-1 shadow-xl">
      {#each ui.workspaces as w}
        <button
          class="flex w-full items-start gap-2 rounded-md px-2.5 py-2 text-left hover:bg-zinc-800"
          onclick={() => pick(w.name)}
        >
          <span class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style="background: {w.color ?? '#10B981'}"></span>
          <span class="flex-1 min-w-0">
            <span class="block truncate font-medium">{w.name}</span>
            {#if w.description}
              <span class="block text-xs text-zinc-400">{w.description}</span>
            {/if}
            <span class="mt-1 flex flex-wrap gap-1 text-[10px] text-zinc-500">
              {#if w.active_skills.length}<span>{w.active_skills.length} skill{w.active_skills.length === 1 ? '' : 's'}</span>{/if}
              {#if w.active_ceps.length}<span>· {w.active_ceps.length} CEP{w.active_ceps.length === 1 ? '' : 's'}</span>{/if}
              {#if w.active_tools?.length}<span>· {w.active_tools.length} tool{w.active_tools.length === 1 ? '' : 's'}</span>{/if}
            </span>
          </span>
          {#if ui.activeWorkspace === w.name}
            <span class="shrink-0 text-emerald-400">✓</span>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>
