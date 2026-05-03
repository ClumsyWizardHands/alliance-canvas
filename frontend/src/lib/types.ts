// Mirrors of backend schemas — keep in sync with shared/schemas/*.json.

export interface Workspace {
  name: string;
  color?: string;
  description?: string;
  folder_mounts: Record<string, string>;
  active_skills: string[];
  active_ceps: string[];
  active_tools?: string[];
  default_crew: string[];
  model_params: { num_ctx?: number; temperature?: number };
  _file?: string;
}

export interface Agent {
  name: string;
  display_name?: string;
  model: string;
  modelfile?: string | null;
  color?: string;
  avatar_emoji?: string;
  connected: boolean;
  machine?: string;
  stub_message?: string;
  tool_allowlist?: string[];
  system_prompt_extra?: string;
  handoff_matrix?: Record<string, string>;
  _modelfile_text?: string | null;
}

export interface SkillIndex {
  slug: string;
  name: string;
  description: string;
  version?: string;
  emoji?: string;
  homepage?: string;
  metadata?: Record<string, unknown>;
  is_folder_format: boolean;
  flat_warning?: string | null;
  body?: string;
}

export type CardType =
  | 'SLUTCard'
  | 'CEPRoutingCard'
  | 'HarvestSummaryCard'
  | 'PrincipleQuoteCard'
  | 'FallbackCard';

export interface Card {
  card_type: CardType | string;
  data: Record<string, any>;
}

export interface ToolCall {
  call_id: string;
  name: string;
  args: Record<string, any>;
  output?: string;
  pending: boolean;
}

export interface MessagePart {
  kind: 'text' | 'card' | 'tool_call' | 'card_error';
  text?: string;
  card?: Card;
  toolCall?: ToolCall;
  error?: string;
  raw?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  agent?: string;
  parts: MessagePart[];
  pending: boolean;
  ts: number;
}

// WS event types from the backend
export type ServerEvent =
  | { type: 'token'; content: string }
  | { type: 'card_start' }
  | { type: 'card'; card: string; data: Record<string, any> }
  | { type: 'card_parse_error'; error: string; raw: string }
  | { type: 'tool_call_start'; name: string; args: Record<string, any>; call_id: string }
  | { type: 'tool_call_end'; name: string; output: string; call_id: string }
  | { type: 'tool_round_limit'; rounds: number }
  | { type: 'error'; message: string }
  | { type: 'done'; message_id: number };
