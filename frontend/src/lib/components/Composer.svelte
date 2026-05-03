<script lang="ts">
  import { api, openTurnSocket } from '../api';
  import { ui, appendUserMessage, newAssistantMessage, applyEvent, getActiveAgent } from '../stores.svelte';

  let value = $state('');
  let sending = $state(false);
  let textarea: HTMLTextAreaElement | null = $state(null);
  let socket: WebSocket | null = null;

  async function send() {
    const text = value.trim();
    if (!text || sending) return;
    const agent = getActiveAgent();
    if (!agent || !agent.connected) {
      ui.messages.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        agent: agent?.name ?? 'system',
        parts: [{ kind: 'text', text: agent?.stub_message ?? 'Active agent is not connected on this machine.' }],
        pending: false,
        ts: Date.now()
      });
      value = '';
      return;
    }

    appendUserMessage(text);
    value = '';
    sending = true;

    try {
      const res = await api.startChat({
        workspace: ui.activeWorkspace,
        agent: agent.name,
        message: text,
        conversation_id: ui.conversationId ?? undefined
      });
      ui.conversationId = res.conversation_id;
      ui.toolsLoaded = res.tools_loaded;

      const m = newAssistantMessage(agent.name);
      socket = openTurnSocket(res.turn_id);

      socket.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data);
          const finished = applyEvent(m, ev);
          if (finished) {
            sending = false;
          }
        } catch (err) {
          console.error('bad WS event', err, e.data);
        }
      };
      socket.onerror = (e) => {
        console.error('WS error', e);
        m.parts.push({ kind: 'text', text: '\n\n**WebSocket error.**' });
        m.pending = false;
        sending = false;
      };
      socket.onclose = () => {
        if (m.pending) {
          m.pending = false;
        }
        sending = false;
      };
    } catch (e: any) {
      const m = newAssistantMessage(agent.name);
      m.parts.push({ kind: 'text', text: `**Failed to start turn:** ${e.message}` });
      m.pending = false;
      sending = false;
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function autosize() {
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(240, textarea.scrollHeight) + 'px';
  }
</script>

<div class="flex items-end gap-2 border-t border-zinc-900 bg-zinc-950 p-3">
  <textarea
    bind:this={textarea}
    bind:value
    oninput={autosize}
    onkeydown={onKeydown}
    rows="1"
    placeholder="Talk to {getActiveAgent()?.display_name ?? 'Archie'} — Enter to send, Shift+Enter for newline"
    class="flex-1 resize-none rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm placeholder:text-zinc-600 focus:border-zinc-700 focus:outline-none"
  ></textarea>
  <button
    class="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
    onclick={send}
    disabled={sending || !value.trim()}
  >
    {sending ? '…' : 'Send'}
  </button>
</div>
