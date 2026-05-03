<script lang="ts">
  let { data }: { data: Record<string, any> } = $props();

  const dist = $derived(data.ripeness_distribution ?? {});
  const total = $derived((dist.green ?? 0) + (dist.red ?? 0) + (dist.purple ?? 0));
  const pct = (n: number) => (total > 0 ? `${Math.round((n / total) * 100)}%` : '0%');
</script>

<article class="my-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 shadow">
  <header class="flex items-baseline justify-between gap-3">
    <h3 class="text-sm font-semibold">{data.source_name ?? 'Harvest'}</h3>
    {#if data.date}<span class="font-mono text-xs text-zinc-400">{data.date}</span>{/if}
  </header>

  <div class="mt-2 flex items-baseline gap-3 text-xs">
    <span class="rounded bg-zinc-900 px-2 py-0.5 font-mono text-zinc-200">
      {data.draft_count ?? 0} drafts
    </span>
    {#if total > 0}
      <span class="text-zinc-400">ripeness:</span>
      <span class="text-emerald-400">🟢 {dist.green ?? 0} ({pct(dist.green ?? 0)})</span>
      <span class="text-rose-400">🔴 {dist.red ?? 0} ({pct(dist.red ?? 0)})</span>
      <span class="text-purple-400">🟣 {dist.purple ?? 0} ({pct(dist.purple ?? 0)})</span>
    {/if}
  </div>

  {#if total > 0}
    <div class="mt-2 flex h-2 overflow-hidden rounded-full bg-zinc-900">
      <div class="bg-emerald-500" style="width: {pct(dist.green ?? 0)}"></div>
      <div class="bg-rose-500"    style="width: {pct(dist.red ?? 0)}"></div>
      <div class="bg-purple-500"  style="width: {pct(dist.purple ?? 0)}"></div>
    </div>
  {/if}

  {#if Array.isArray(data.streams) && data.streams.length}
    <div class="mt-2.5 flex flex-wrap gap-1.5">
      {#each data.streams as s}
        <span class="rounded bg-zinc-900 px-2 py-0.5 text-xs text-zinc-300">{s}</span>
      {/each}
    </div>
  {/if}
</article>
