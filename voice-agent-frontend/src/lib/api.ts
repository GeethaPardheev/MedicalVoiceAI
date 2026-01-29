import type { SummaryRecord } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type FetchOptions = RequestInit & { json?: Record<string, unknown> };

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  console.info("[api] request", { url: `${API_BASE_URL}${path}`, method, body: options.json ?? options.body });
  const start = performance.now();
  const headers = new Headers(options.headers);
  if (options.json) {
    headers.set("Content-Type", "application/json");
  }
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body: options.json ? JSON.stringify(options.json) : options.body,
    });
    const duration = Math.round(performance.now() - start);
    console.info("[api] response", { url: `${API_BASE_URL}${path}`, status: response.status, durationMs: duration });
    if (!response.ok) {
      throw new Error(`API error ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("[api] request failed", { url: `${API_BASE_URL}${path}`, method, error });
    throw error;
  }
}

export type SessionPayload = {
  display_name: string;
  phone_number: string;
  room_name?: string;
};

export type SessionResponse = {
  room_name: string;
  identity: string;
  token: string;
  expires_at: number;
  livekit_url: string;
};

export async function requestSession(payload: SessionPayload): Promise<SessionResponse> {
  return apiFetch<SessionResponse>("/api/session", { method: "POST", json: payload });
}

export async function fetchSummaries(phone?: string, limit = 3): Promise<SummaryRecord[]> {
  const query = new URLSearchParams();
  if (phone) {
    query.set("phone", phone);
  }
  query.set("limit", String(limit));
  return apiFetch(`/api/summaries?${query.toString()}`);
}

export type BackendConfig = {
  livekit_url: string;
  default_timezone: string;
};

export async function fetchConfig(): Promise<BackendConfig> {
  return apiFetch("/api/config");
}
