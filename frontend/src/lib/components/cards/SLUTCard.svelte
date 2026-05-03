<script lang="ts">
  import Markdown from '../Markdown.svelte';
  let { data }: { data: Record<string, any> } = $props();

  const ripeness = $derived((data.ripeness ?? 'green').toString().toLowerCase());
  const ripenessConfig: Record<string, { emoji: string; bg: string; ring: string; label: string }> = {
    green:  { emoji: '🟢', bg: 'bg-emerald-500/10',  ring: 'ring-emerald-500/40', label: 'Green — articulated, untested' },
    red:    { emoji: '🔴', bg: 'bg-rose-500/10',     ring: 'ring-rose-500/40',    label: 'Red — operating as infrastructure' },
    purple: { emoji: '🟣', bg: 'bg-purple-500/10',   ring: 'ring-purple-500/40',  label: 'Purple — tested, foundational' }
  };
  const r = $derived(ripenessConfig[ripeness] ?? ripenessConfig.green);

  // Accept either nested `triple_helix.{pollination,...}` or flat `triple_helix_*` keys
  // because models drift between shapes. Same for body/body_md and anchors.
  const helix = $derived({
    pollination:
      data.triple_helix?.pollination ?? data.triple_helix_pollination ?? data.pollination,
    offensive_resilience:
      data.triple_helix?.offensive_resilience ??
      data.triple_helix_offensive_resilience ??
      data.offensive_resilience,
    multiversal_grounding:
      data.triple_helix?.multiversal_grounding ??
      data.triple_helix_multiversal_grounding ??
      data.multiversal_grounding
  });
  const anchors = $derived({
    backward: data.cep_anchors?.backward ?? data.cep_anchor_backward ?? data.backward,
    present:  data.cep_anchors?.present  ?? data.cep_anchor_present  ?? data.present,
    forward:  data.cep_anchors?.forward  ?? data.cep_anchor_forward  ?? data.forward
  });
  const bodyText = $derived(
    data.body_md ?? data.body ?? data.principle ?? ''
  );
  const slipknots = $derived(
    Array.isArray(data.slipknots)
      ? data.slipknots
      : Array.isArray(data.slip_knots)
        ? data.slip_knots
        : []
  );
</script>

<article class={`my-3 rounded-xl border border-zinc-800 ${r.bg} ring-1 ${r.ring} p-4 shadow-lg`}>
  <header class="flex items-baseline justify-between gap-3">
    <h3 class="text-base font-semibold leading-tight">{data.title ?? 'Untitled SLUT'}</h3>
    <span class="shrink-0 rounded-full bg-zinc-900 px-2 py-0.5 text-xs font-medium" title={r.label}>
      {r.emoji} <span class="capitalize">{ripeness}</span>
    </span>
  </header>

  {#if data.origin_speaker}
    <div class="mt-1 text-xs text-zinc-400">Origin — {data.origin_speaker}</div>
  {/if}

  <div class="mt-3 grid gap-3 sm:grid-cols-3">
    <div class="rounded-md bg-zinc-900/60 p-2.5">
      <div class="text-[10px] uppercase tracking-wider text-zinc-500">Pollination</div>
      <div class="mt-1 text-xs leading-snug text-zinc-200">{helix.pollination ?? '—'}</div>
    </div>
    <div class="rounded-md bg-zinc-900/60 p-2.5">
      <div class="text-[10px] uppercase tracking-wider text-zinc-500">Offensive Resilience</div>
      <div class="mt-1 text-xs leading-snug text-zinc-200">{helix.offensive_resilience ?? '—'}</div>
    </div>
    <div class="rounded-md bg-zinc-900/60 p-2.5">
      <div class="text-[10px] uppercase tracking-wider text-zinc-500">Multiversal Grounding</div>
      <div class="mt-1 text-xs leading-snug text-zinc-200">{helix.multiversal_grounding ?? '—'}</div>
    </div>
  </div>

  {#if anchors.backward || anchors.present || anchors.forward}
    <div class="mt-3 flex flex-col gap-1.5 rounded-md border border-zinc-800/80 bg-zinc-950/50 p-2.5">
      <div class="text-[10px] uppercase tracking-wider text-zinc-500">CEP anchors</div>
      <div class="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-xs leading-snug">
        <span class="text-zinc-500">←</span><span class="text-zinc-300">{anchors.backward ?? '—'}</span>
        <span class="text-zinc-500">●</span><span class="text-zinc-300">{anchors.present ?? '—'}</span>
        <span class="text-zinc-500">→</span><span class="text-zinc-300">{anchors.forward ?? '—'}</span>
      </div>
    </div>
  {/if}

  {#if bodyText}
    <div class="mt-3">
      <Markdown text={bodyText} />
    </div>
  {/if}

  {#if slipknots.length}
    <div class="mt-3 flex flex-wrap gap-1.5 border-t border-zinc-800 pt-2.5">
      <span class="text-[10px] uppercase tracking-wider text-zinc-500">Slipknots</span>
      {#each slipknots as sk}
        <span class="rounded bg-zinc-900 px-1.5 py-0.5 font-mono text-[11px] text-blue-300">{sk}</span>
      {/each}
    </div>
  {/if}
</article>
