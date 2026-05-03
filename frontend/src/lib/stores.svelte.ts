// Svelte 5 runes-based stores. Singleton-ish pattern: one global state object
// per concern, exported so components can read/write reactively.

import type { Agent, ChatMessage, ServerEvent, Workspace } from './types';

interface UIState {
  workspaces: Workspace[];
  agents: Agent[];
  activeWorkspace: string;
  activeAgent: string;
  messages: ChatMessage[];
  conversationId: number | null;
  rightPanel: null | 'ledger' | 'skills' | 'principles' | 'agent';
  health: any;
  toolsLoaded: any[];
}

export const ui = $state<UIState>({
  workspaces: [],
  agents: [],
  activeWorkspace: 'Default',
  activeAgent: 'archie',
  messages: [],
  conversationId: null,
  rightPanel: null,
  health: null,
  toolsLoaded: []
});

export function getActiveAgent(): Agent | undefined {
  return ui.agents.find((a) => a.name === ui.activeAgent);
}

export function getActiveWorkspace(): Workspace | undefined {
  return ui.workspaces.find((w) => w.name === ui.activeWorkspace);
}

export function newAssistantMessage(agent: string): ChatMessage {
  const m: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    agent,
    parts: [],
    pending: true,
    ts: Date.now()
  };
  ui.messages.push(m);
  return m;
}

export function appendUserMessage(text: string): ChatMessage {
  const m: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    parts: [{ kind: 'text', text }],
    pending: false,
    ts: Date.now()
  };
  ui.messages.push(m);
  return m;
}

/**
 * Reduce a single server event into the assistant message's parts list.
 * Mutates the message in place (Svelte's reactivity tracks the reference).
 */
export function applyEvent(msg: ChatMessage, ev: ServerEvent): boolean {
  switch (ev.type) {
    case 'token': {
      // Coalesce consecutive text parts
      const last = msg.parts[msg.parts.length - 1];
      if (last && last.kind === 'text') {
        last.text = (last.text ?? '') + ev.content;
      } else {
        msg.parts.push({ kind: 'text', text: ev.content });
      }
      return false;
    }
    case 'card_start':
      // No-op for now (could show a "card forming…" placeholder)
      return false;
    case 'card':
      msg.parts.push({ kind: 'card', card: { card_type: ev.card, data: ev.data } });
      return false;
    case 'card_parse_error':
      msg.parts.push({ kind: 'card_error', error: ev.error, raw: ev.raw });
      return false;
    case 'tool_call_start':
      msg.parts.push({
        kind: 'tool_call',
        toolCall: { call_id: ev.call_id, name: ev.name, args: ev.args, pending: true }
      });
      return false;
    case 'tool_call_end': {
      // Find the most recent matching tool_call part and complete it
      for (let i = msg.parts.length - 1; i >= 0; i--) {
        const p = msg.parts[i];
        if (p.kind === 'tool_call' && p.toolCall?.call_id === ev.call_id && p.toolCall.pending) {
          p.toolCall.output = ev.output;
          p.toolCall.pending = false;
          break;
        }
      }
      return false;
    }
    case 'tool_round_limit':
      msg.parts.push({
        kind: 'text',
        text: `\n\n_(Tool round limit reached after ${ev.rounds} rounds. CEP-13 applies.)_`
      });
      return false;
    case 'error':
      msg.parts.push({ kind: 'text', text: `\n\n**Error:** ${ev.message}` });
      msg.pending = false;
      return true;
    case 'done':
      msg.pending = false;
      return true;
    default:
      return false;
  }
}
