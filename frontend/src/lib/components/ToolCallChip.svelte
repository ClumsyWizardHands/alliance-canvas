<script lang="ts">
  import type { ToolCall } from '../types';
  let { tc }: { tc: ToolCall } = $props();
  let expanded = $state(false);

  function argSummary(args: Record<string, any>): string {
    const keys = Object.keys(args);
    if (keys.length === 0) return '()';
    const previews = keys.map((k) => {
      const v = args[k];
      const s = typeof v === 'string' ? `"${v}"` : JSON.stringify(v);
      return `${k}=${s.length > 40 ? s.slice(0, 37) + '…' : s}`;
    });
    return '(' + previews.join(', ') + ')';
  }
</script>

<div class="my-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-sm font-mono">
  <button
    class="flex w-full items-start gap-2 text-left"
    onclick={() => (expanded = !expanded)}
  >
    <span class="shrink-0 text-zinc-500">{expanded ? '▾' : '▸'}</span>
    <span class="shrink-0">⚙</span>
    <span class="flex-1 truncate">
      <span class="text-emerald-400">{tc.name}</span><span class="text-zinc-400">{argSummary(tc.args)}</span>
    </span>
    {#if tc.pending}
      <span class="shrink-0 animate-pulse text-amber-400">running…</span>
    {:else}
      <span class="shrink-0 text-zinc-500">{tc.output ? `${tc.output.length}ch` : 'done'}</span>
    {/if}
  </button>

  {#if expanded}
    <div class="mt-2 space-y-2">
      <div>
        <div class="text-xs uppercase tracking-wide text-zinc-500">arguments</div>
        <pre class="mt-1 whitespace-pre-wrap text-xs text-zinc-300">{JSON.stringify(tc.args, null, 2)}</pre>
      </div>
      {#if tc.output}
        <div>
          <div class="text-xs uppercase tracking-wide text-zinc-500">output</div>
          <pre class="mt-1 max-h-96 overflow-y-auto whitespace-pre-wrap text-xs text-zinc-300">{tc.output}</pre>
        </div>
      {/if}
    </div>
  {/if}
</div>
