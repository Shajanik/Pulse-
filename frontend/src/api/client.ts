import type { JoinResponse, PollSummary, PublicPoll, ResultsPayload } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (options.auth) {
    const token = localStorage.getItem("pulse_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json() : null;

  if (!res.ok) {
    const message = body?.error ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, message);
  }

  return body as T;
}

export const api = {
  signup: (email: string, password: string) =>
    request<{ token: string; email: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ token: string; email: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  createPoll: (question: string, options: string[], expiresInMinutes: number) =>
    request<PollSummary>("/polls", {
      method: "POST",
      auth: true,
      body: JSON.stringify({ question, options, expiresInMinutes }),
    }),

  myPolls: () => request<PollSummary[]>("/polls/mine", { auth: true }),

  getPoll: (code: string) => request<PublicPoll>(`/polls/${code}`),

  getResults: (code: string) => request<ResultsPayload>(`/polls/${code}/results`),

  joinRoom: (code: string, nickname: string) =>
    request<JoinResponse>(`/rooms/${code}/join`, {
      method: "POST",
      body: JSON.stringify({ nickname }),
    }),

  castVote: (code: string, optionId: string, voterId: string, nickname: string) =>
    request<{ success: boolean }>(`/rooms/${code}/vote`, {
      method: "POST",
      body: JSON.stringify({ optionId, voterId, nickname }),
    }),
};
