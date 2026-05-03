<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { ui } from '$lib/stores.svelte';
  import TopBar from '$lib/components/TopBar.svelte';
  import CrewSidebar from '$lib/components/CrewSidebar.svelte';
  import ChatStream from '$lib/components/ChatStream.svelte';
  import Composer from '$lib/components/Composer.svelte';
  import SidePanel from '$lib/components/SidePanel.svelte';

  let bootError = $state<string | null>(null);

  onMount(async () => {
    try {
      const [w, a, h] = await Promise.all([api.workspaces(), api.agents(), api.health()]);
      ui.workspaces = w.workspaces;
      ui.agents = a.agents;
      ui.health = h;
      if (!ui.workspaces.find((x) => x.name === ui.activeWorkspace) && ui.workspaces.length) {
        ui.activeWorkspace = ui.workspaces[0].name;
      }
      // Default to the first connected agent (single-agent setups land here naturally)
      const first = ui.agents.find((x) => x.connected);
      if (first) ui.activeAgent = first.name;
    } catch (e: any) {
      bootError = e.message;
    }
  });

  // Show the crew sidebar only when there are multiple agents to switch between
  const showCrewSidebar = $derived(ui.agents.filter((a) => a.connected).length > 1);
</script>

<div class="flex h-screen flex-col">
  <TopBar />

  {#if bootError}
    <div class="border-b border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-200">
      Backend boot error: {bootError} — is the backend running on :5181?
    </div>
  {/if}

  <div class="flex flex-1 overflow-hidden">
    {#if showCrewSidebar}
      <CrewSidebar />
    {/if}
    <main class="flex flex-1 flex-col">
      <ChatStream />
      <Composer />
    </main>
    <SidePanel />
  </div>
</div>
