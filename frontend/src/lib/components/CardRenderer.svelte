<script lang="ts">
  import type { Card } from '../types';
  import SLUTCard from './cards/SLUTCard.svelte';
  import CEPRoutingCard from './cards/CEPRoutingCard.svelte';
  import HarvestSummaryCard from './cards/HarvestSummaryCard.svelte';
  import PrincipleQuoteCard from './cards/PrincipleQuoteCard.svelte';
  import FallbackCard from './cards/FallbackCard.svelte';

  let { card }: { card: Card } = $props();
</script>

{#if card.card_type === 'SLUTCard'}
  <SLUTCard data={card.data} />
{:else if card.card_type === 'CEPRoutingCard'}
  <CEPRoutingCard data={card.data} />
{:else if card.card_type === 'HarvestSummaryCard'}
  <HarvestSummaryCard data={card.data} />
{:else if card.card_type === 'PrincipleQuoteCard'}
  <PrincipleQuoteCard data={card.data} />
{:else}
  <FallbackCard data={card.data} cardType={card.card_type} />
{/if}
