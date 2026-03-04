/**
 * frontend/src/lib/api.ts
 * Faz 6 — API Client
 * JWT token'ı localStorage'dan okur, her isteğe Authorization header ekler.
 * 401 → login sayfasına yönlendirir.
 */

import type {
  Membro,
  CreateMembroPayload,
  UpdateMembroPayload,
  Meeting,
  KnowledgeDoc,
  ChatMessage,
  ChatRequest,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── Token Helpers ───────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setTokens(accessToken: string, email?: string): void {
  localStorage.setItem("access_token", accessToken);
  if (email) localStorage.setItem("user_email", email);
  document.cookie = `access_token=${accessToken}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
}

export function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_email");
  document.cookie = "access_token=; path=/; max-age=0; SameSite=Lax";
}

// ─── Base Fetch ──────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; token_type: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
};

// ─── Membro ──────────────────────────────────────────────────────────────────

export const membroApi = {
  list: () => apiFetch<Membro[]>("/api/v1/membros/"),

  get: (id: string) => apiFetch<Membro>(`/api/v1/membros/${id}`),

  create: (payload: CreateMembroPayload) =>
    apiFetch<Membro>("/api/v1/membros/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  update: (id: string, payload: UpdateMembroPayload) =>
    apiFetch<Membro>(`/api/v1/membros/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/api/v1/membros/${id}`, { method: "DELETE" }),
};

// ─── Chat ────────────────────────────────────────────────────────────────────

export const chatApi = {
  /** Geçmiş mesajları çeker */
  history: (membroId: string) =>
    apiFetch<ChatMessage[]>(`/api/v1/chat/?membro_id=${membroId}`),

  /** Streaming chat — ReadableStream döner */
  stream: async (payload: ChatRequest): Promise<ReadableStream<Uint8Array>> => {
    const token = getAccessToken();

    const res = await fetch(`${API_BASE}/api/v1/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }

    return res.body;
  },
};

// ─── Meetings ────────────────────────────────────────────────────────────────

export const meetingApi = {
  create: (membroId: string, title?: string) =>
    apiFetch<Meeting>("/api/v1/meetings/", {
      method: "POST",
      body: JSON.stringify({ membro_id: membroId, title }),
    }),

  list: () => apiFetch<Meeting[]>("/api/v1/meetings/"),

  end: (id: string) =>
    apiFetch<Meeting>(`/api/v1/meetings/${id}/end`, { method: "POST" }),
};

// ─── Knowledge ───────────────────────────────────────────────────────────────

export const knowledgeApi = {
  list: (membroId?: string) => {
    const qs = membroId ? `?membro_id=${membroId}` : "";
    return apiFetch<KnowledgeDoc[]>(`/api/v1/knowledge/docs${qs}`);
  },

  create: (payload: { membro_id: string; content: string; title?: string }) =>
    apiFetch<KnowledgeDoc>("/api/v1/knowledge/docs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/api/v1/knowledge/docs/${id}`, { method: "DELETE" }),
};
