<script lang="ts">
  let { data, cardType }: { data: Record<string, any>; cardType?: string } = $props();
</script>

<article class="my-3 rounded-xl border border-zinc-700 bg-zinc-900/60 p-3.5">
  <div class="text-[10px] uppercase tracking-wider text-zinc-500">
    Unknown card type — {cardType ?? 'no type'}
  </div>
  <pre class="mt-1.5 max-h-72 overflow-auto whitespace-pre-wrap text-xs text-zinc-300">{JSON.stringify(
    data,
    null,
    2
  )}</pre>
</article>
