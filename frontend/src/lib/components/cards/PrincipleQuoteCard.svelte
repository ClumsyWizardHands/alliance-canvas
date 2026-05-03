<script lang="ts">
  import Markdown from '../Markdown.svelte';
  let { data }: { data: Record<string, any> } = $props();

  const stackColor: Record<string, string> = {
    kernel:    'bg-emerald-500/20 text-emerald-200',
    rgt:       'bg-cyan-500/20 text-cyan-200',
    applied:   'bg-amber-500/20 text-amber-200',
    skill:     'bg-violet-500/20 text-violet-200',
    protocols: 'bg-blue-500/20 text-blue-200'
  };
  const stack = $derived((data.stack ?? 'kernel').toLowerCase());
  const cls = $derived(stackColor[stack] ?? stackColor.kernel);
  let expanded = $state(false);
</script>

<article class="my-3 rounded-xl border border-zinc-800 bg-zinc-900/40 p-3.5">
  <header class="flex items-baseline gap-2">
    <span class={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${cls}`}>
      {stack}
    </span>
    <span class="font-mono text-sm text-zinc-200">{data.slug ?? '?'}</span>
    {#if data.title}<span class="text-xs text-zinc-400">— {data.title}</span>{/if}
  </header>

  <div class={`mt-2 ${expanded ? '' : 'line-clamp-3'}`}>
    <Markdown text={data.quote ?? data.body ?? ''} />
  </div>
  <button
    class="mt-1 text-xs text-zinc-400 hover:text-zinc-200"
    onclick={() => (expanded = !expanded)}
  >
    {expanded ? 'collapse' : 'expand'}
  </button>
</article>
