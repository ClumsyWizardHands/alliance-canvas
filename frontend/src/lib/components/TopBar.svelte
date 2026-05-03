<script lang="ts">
  import { ui, getActiveAgent } from '../stores.svelte';
  import WorkspaceSwitcher from './WorkspaceSwitcher.svelte';

  function toggle(panel: 'ledger' | 'skills' | 'principles' | 'agent') {
    ui.rightPanel = ui.rightPanel === panel ? null : panel;
  }

  const agent = $derived(getActiveAgent());
</script>

<header class="flex items-center justify-between border-b border-zinc-900 bg-zinc-950 px-4 py-2">
  <div class="flex items-center gap-3">
    <span class="font-semibold tracking-tight">Alliance Canvas</span>
    <WorkspaceSwitcher />
    {#if agent}
      <button
        class={`flex items-center gap-1.5 rounded-md border border-zinc-800 px-2 py-1 text-xs hover:bg-zinc-900 ${ui.rightPanel === 'agent' ? 'bg-zinc-900' : ''}`}
        onclick={() => toggle('agent')}
        title="Click to inspect this agent's identity"
      >
        <span>{agent.avatar_emoji ?? '·'}</span>
        <span class="font-medium" style="color: {agent.color ?? '#10B981'}">{agent.display_name ?? agent.name}</span>
      </button>
    {/if}
  </div>

  <div class="flex items-center gap-2 text-xs">
    <button
      class={`rounded-md px-2 py-1 hover:bg-zinc-900 ${ui.rightPanel === 'ledger' ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-400'}`}
      onclick={() => toggle('ledger')}
    >
      ledger
    </button>
    <button
      class={`rounded-md px-2 py-1 hover:bg-zinc-900 ${ui.rightPanel === 'skills' ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-400'}`}
      onclick={() => toggle('skills')}
    >
      skills
    </button>
    <button
      class={`rounded-md px-2 py-1 hover:bg-zinc-900 ${ui.rightPanel === 'principles' ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-400'}`}
      onclick={() => toggle('principles')}
    >
      principles
    </button>
    <span class="ml-3 text-[10px] uppercase tracking-wider text-zinc-600">
      {#if ui.health}
        ollama {ui.health.ollama?.reachable ? '●' : '○'}
      {/if}
    </span>
  </div>
</header>
