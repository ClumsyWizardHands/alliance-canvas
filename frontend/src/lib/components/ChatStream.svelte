<script lang="ts">
  import { tick } from 'svelte';
  import { ui } from '../stores.svelte';
  import MessageBubble from './MessageBubble.svelte';

  let scroller: HTMLDivElement | null = $state(null);

  $effect(() => {
    void ui.messages.length;
    void ui.messages.at(-1)?.parts.length;
    void ui.messages.at(-1)?.parts.at(-1);
    tick().then(() => {
      if (scroller) scroller.scrollTop = scroller.scrollHeight;
    });
  });

  function agentFor(name?: string) {
    return ui.agents.find((a) => a.name === name);
  }
</script>

<div bind:this={scroller} class="flex-1 overflow-y-auto">
  <div class="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
    {#if ui.messages.length === 0}
      <div class="rounded-xl border border-zinc-900 bg-zinc-950/40 p-6 text-sm text-zinc-400">
        <div class="mb-2 font-semibold text-zinc-200">Alliance Canvas</div>
        <p>Local Ollama-backed chat with empire's Alliance. Talk to Archie. Type a question, ask him to load a skill, or paste material to harvest.</p>
        <p class="mt-3 text-xs text-zinc-500">
          Try: "use ecosystem_glossary to define SLUT" · "load the slut-harvest skill" · "switch workspace to Daily Harvest then list skills"
        </p>
      </div>
    {/if}

    {#each ui.messages as m (m.id)}
      <MessageBubble msg={m} agent={agentFor(m.agent)} />
    {/each}
  </div>
</div>
