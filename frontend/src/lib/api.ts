// Thin wrapper around the backend REST + WS API. Same-origin via Vite proxy in
// dev; in built mode the FastAPI server can serve the static bundle alongside
// the API on :5181.

import type { Workspace, Agent, SkillIndex } from './types';

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} → ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function jput<T>(path: string, body: any): Promise<T> {
  const r = await fetch(path, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`${path} → ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function jpost<T>(path: string, body: any): Promise<T> {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`${path} → ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => jget<{ version: string; ollama: any; workspace_count: number; agent_count: number }>('/api/health'),
  workspaces: () => jget<{ workspaces: Workspace[] }>('/api/workspaces'),
  workspace: (name: string) => jget<Workspace>(`/api/workspaces/${encodeURIComponent(name)}`),
  putWorkspace: (name: string, body: Partial<Workspace>) =>
    jput<Workspace>(`/api/workspaces/${encodeURIComponent(name)}`, body),
  agents: () => jget<{ agents: Agent[] }>('/api/agents'),
  agent: (name: string) => jget<Agent>(`/api/agents/${encodeURIComponent(name)}`),
  skills: (workspace: string) =>
    jget<{ workspace: string; skills_dir: string; skills: SkillIndex[] }>(
      `/api/skills?workspace=${encodeURIComponent(workspace)}`
    ),
  skill: (slug: string, workspace: string) =>
    jget<SkillIndex & { body: string }>(
      `/api/skills/${encodeURIComponent(slug)}?workspace=${encodeURIComponent(workspace)}`
    ),
  principles: (workspace: string) =>
    jget<{ principles: { slug: string; title: string; stack: string; path: string }[] }>(
      `/api/principles?workspace=${encodeURIComponent(workspace)}`
    ),
  principle: (slug: string, workspace: string) =>
    jget<{ slug: string; stack: string; body: string }>(
      `/api/principles/${encodeURIComponent(slug)}?workspace=${encodeURIComponent(workspace)}`
    ),
  ledger: (n = 50) => jget<{ meta: any; entries: any[] }>(`/api/ledger?n=${n}`),
  startChat: (body: { workspace: string; agent: string; message: string; conversation_id?: number }) =>
    jpost<{ turn_id: string; conversation_id: number; ws_url: string; tools_loaded: any[] }>(
      '/api/chat',
      body
    )
};

export function openTurnSocket(turn_id: string): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return new WebSocket(`${proto}://${window.location.host}/api/chat/stream/${turn_id}`);
}
