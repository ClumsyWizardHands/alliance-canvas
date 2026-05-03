<script lang="ts">
  let { data }: { data: Record<string, any> } = $props();
</script>

<article class="my-3 rounded-xl border border-blue-500/30 bg-blue-500/10 p-3.5 shadow">
  <div class="flex items-baseline gap-2">
    <span class="rounded bg-blue-500/20 px-1.5 py-0.5 font-mono text-[11px] text-blue-200">CEP routing</span>
    <span class="font-mono text-sm text-blue-100">{data.cep_slug ?? 'cep-??'}</span>
  </div>

  <div class="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-xs">
    {#if data.task}
      <span class="text-zinc-500">task</span><span class="text-zinc-200">{data.task}</span>
    {/if}
    {#if data.matched_trigger}
      <span class="text-zinc-500">trigger</span><span class="text-zinc-200">{data.matched_trigger}</span>
    {/if}
    {#if data.summary}
      <span class="text-zinc-500">summary</span><span class="text-zinc-200">{data.summary}</span>
    {/if}
  </div>
</article>
