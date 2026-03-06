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
  SysMembro,
  SysSkillWithStatus,
  Integration,
  CreateIntegrationPayload,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── Tenant Helpers ──────────────────────────────────────────────────────────

/**
 * Tarayıcı hostname'inden tenant slug'ını çıkarır.
 * testco.localhost   → "testco"
 * testco.themembro.com → "testco"
 * localhost          → null  (geliştirme / public)
 */
export function getTenantSlug(): string | null {
  if (typeof window === "undefined") return null;
  const parts = window.location.hostname.split(".");
  // En az 2 parça ve ilk parça "localhost" veya "www" değilse slug kabul et
  if (parts.length >= 2 && parts[0] !== "localhost" && parts[0] !== "www") {
    return parts[0];
  }
  return null;
}

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

  // Tenant slug'ı her zaman gönder — backend tenant_middleware için zorunlu
  const slug = getTenantSlug();
  if (slug) {
    headers["X-Tenant-Slug"] = slug;
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
    apiFetch<{ access_token: string; token_type: string; role: string }>("/api/v1/auth/login", {
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

// ─── SYS Membros ───────────────────────────────────────────────────────────

export const sysMembroApi = {
  /** Tüm sistem şablonlarını listeler. Auth gerektirmez. */
  list: () => apiFetch<SysMembro[]>("/api/v1/sys-membros/"),

  /** Şablonun skill listesini tenant entegrasyon durumuyla döndürür. */
  getSkills: (sysMembroId: string) =>
    apiFetch<SysSkillWithStatus[]>(`/api/v1/sys-membros/${sysMembroId}/skills`),
};

// ─── Integrations ──────────────────────────────────────────────────────────

export const integrationApi = {
  list: () => apiFetch<Integration[]>("/api/v1/integrations/"),

  create: (payload: CreateIntegrationPayload) =>
    apiFetch<Integration>("/api/v1/integrations/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/api/v1/integrations/${id}`, { method: "DELETE" }),
};

// ─── Chat ────────────────────────────────────────────────────────────────────

export const chatApi = {
  /** Geçmiş mesajları çeker — son 50 mesaj, eski→yeni sıralı */
  history: (membroId: string): Promise<ChatMessage[]> =>
    apiFetch<ChatMessage[]>(`/api/v1/agents/${membroId}/history`),

  /** Streaming chat — SSE akışından token'ları çıkarır, saf metin döner */
  stream: async (membroId: string, payload: ChatRequest): Promise<ReadableStream<Uint8Array>> => {
    const token = getAccessToken();

    const slug = getTenantSlug();
    const res = await fetch(`${API_BASE}/api/v1/agents/${membroId}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(slug ? { "X-Tenant-Slug": slug } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!res.ok || !res.body) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody?.detail ?? `HTTP ${res.status}`);
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
