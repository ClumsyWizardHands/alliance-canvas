<script lang="ts">
  import type { Agent, ChatMessage } from '../types';
  import Markdown from './Markdown.svelte';
  import ToolCallChip from './ToolCallChip.svelte';
  import CardRenderer from './CardRenderer.svelte';

  let { msg, agent }: { msg: ChatMessage; agent?: Agent } = $props();

  const color = $derived(agent?.color ?? '#10B981');
  const emoji = $derived(agent?.avatar_emoji ?? '🟢');
  const displayName = $derived(agent?.display_name ?? agent?.name ?? 'archie');
</script>

{#if msg.role === 'user'}
  <div class="flex justify-end">
    <div class="max-w-[85%] rounded-2xl bg-zinc-800 px-4 py-2.5 text-sm">
      {#each msg.parts as p}
        {#if p.kind === 'text'}<Markdown text={p.text ?? ''} />{/if}
      {/each}
    </div>
  </div>
{:else}
  <div class="flex flex-col gap-1">
    <div class="flex items-baseline gap-2 text-xs">
      <span style:color>{emoji}</span>
      <span class="font-medium" style:color>{displayName}</span>
      {#if msg.pending}
        <span class="animate-pulse text-zinc-500">streaming…</span>
      {/if}
    </div>
    <div
      class="max-w-[95%] rounded-2xl border-l-2 bg-zinc-950/40 px-4 py-2.5 text-sm"
      style="border-color: {color}"
    >
      {#each msg.parts as p}
        {#if p.kind === 'text'}
          <Markdown text={p.text ?? ''} />
        {:else if p.kind === 'tool_call' && p.toolCall}
          <ToolCallChip tc={p.toolCall} />
        {:else if p.kind === 'card' && p.card}
          <CardRenderer card={p.card} />
        {:else if p.kind === 'card_error'}
          <div class="my-2 rounded border border-rose-500/40 bg-rose-500/10 p-2 text-xs">
            <span class="font-mono text-rose-300">card parse error:</span> {p.error}
            {#if p.raw}
              <pre class="mt-1 max-h-40 overflow-auto whitespace-pre-wrap text-zinc-300">{p.raw}</pre>
            {/if}
          </div>
        {/if}
      {/each}
    </div>
  </div>
{/if}
