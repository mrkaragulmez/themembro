/**
 * frontend/src/types/index.ts
 * Faz 6 — Proje genelinde kullanılan TypeScript tipleri
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  role: "owner" | "admin" | "member";
}

// ─── Membro ──────────────────────────────────────────────────────────────────

export type MembroStatus = "active" | "inactive" | "archived";

// 8 renk paleti — membro avatarları için
export const MEMBRO_COLORS = [
  "#655F9C", // periwinkle
  "#FF6F80", // coral
  "#34B27A", // green
  "#F59E0B", // amber
  "#3B82F6", // blue
  "#EC4899", // pink
  "#8B5CF6", // violet
  "#14B8A6", // teal
] as const;

export interface Membro {
  id: string;
  name: string;
  persona: string;
  system_prompt: string;
  status: MembroStatus;
  color: string;               // MEMBRO_COLORS'dan biri
  tools: string[];             // MCP skill name'leri
  last_interaction_at: string | null;
  created_at: string;
  tenant_id: string;
}

export interface CreateMembroPayload {
  name: string;
  persona: string;
  system_prompt: string;
  tools: string[];
  color?: string;
}

export interface UpdateMembroPayload extends Partial<CreateMembroPayload> {
  status?: MembroStatus;
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export type ChatRole = "user" | "assistant" | "tool_call" | "tool_result" | "error";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  tool_name?: string;         // tool_call için
  created_at: string;
  membro_id: string;
}

export interface ChatRequest {
  membro_id: string;
  message: string;
}

// ─── Meeting ─────────────────────────────────────────────────────────────────

export type MeetingStatus = "active" | "ended";

export interface Meeting {
  id: string;
  membro_id: string;
  room_name: string;
  livekit_url: string;
  token: string;
  status: MeetingStatus;
  started_at: string;
  ended_at: string | null;
  tenant_id: string;
}

export interface MeetingTranscriptLine {
  id: string;
  meeting_id: string;
  speaker: "user" | "membro";
  text: string;
  created_at: string;
}

// ─── Knowledge ───────────────────────────────────────────────────────────────

export interface KnowledgeDoc {
  id: string;
  membro_id: string;
  title: string;
  content_type: "text" | "url" | "file";
  source: string;
  created_at: string;
  tenant_id: string;
}

// ─── Activity Feed ───────────────────────────────────────────────────────────

export type ActivityType = "chat" | "meeting" | "knowledge" | "tool_call";

export interface ActivityItem {
  id: string;
  type: ActivityType;
  membro_id: string;
  membro_name: string;
  membro_color: string;
  description: string;
  created_at: string;
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
