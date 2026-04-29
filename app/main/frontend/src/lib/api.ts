import { ENV } from "@/config/env";
import { authStorage } from "@/lib/auth-storage";
import type {
  User,
  Call,
  CallDetail,
  Check,
  IntegrationLog,
  IntegrationStatus,
} from "@/types";

const BASE = ENV.BACKEND_URL || "/api";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

interface RefreshResponse {
  access_token: string;
  token_type: string;
}

function authHeader(): Record<string, string> {
  const token = authStorage.getAccess();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function tryRefresh(): Promise<string | null> {
  const refresh = authStorage.getRefresh();
  if (!refresh) return null;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as RefreshResponse;
  authStorage.setTokens(data.access_token);
  return data.access_token;
}

function handleAuthFailure() {
  authStorage.clear();
  if (typeof window !== "undefined" && !window.location.pathname.endsWith("/login")) {
    window.location.href = "/main/login";
  }
}

async function rawFetch(url: string, init: RequestInit, withJsonCT: boolean): Promise<Response> {
  const baseHeaders: Record<string, string> = { ...authHeader() };
  if (withJsonCT) baseHeaders["Content-Type"] = "application/json";
  return fetch(url, {
    ...init,
    headers: { ...baseHeaders, ...(init.headers as Record<string, string> | undefined) },
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const opts = init ?? {};

  let res = await rawFetch(url, opts, true);

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const newToken = await tryRefresh();
    if (newToken) {
      res = await rawFetch(url, opts, true);
    } else {
      handleAuthFailure();
      throw new Error("Требуется авторизация");
    }
  }

  if (!res.ok) {
    let message: string;
    try {
      const data = await res.json();
      message = data.detail || JSON.stringify(data);
    } catch {
      message = `Сервер вернул ${res.status}`;
    }
    if (res.status === 401 && !path.startsWith("/auth/")) handleAuthFailure();
    throw new Error(message);
  }

  return res.json();
}

export const authApi = {
  login: (phone_number: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ phone_number, password }),
    }),
  me: () => request<User>("/auth/me"),
  logout: () => {
    authStorage.clear();
  },
};

export const usersApi = {
  list: (role?: string) => {
    const params = role ? `?role=${role}` : "";
    return request<User[]>(`/users/${params}`);
  },
  get: (id: number) => request<User>(`/users/${id}`),
  create: (data: { name: string; phone_number?: string; role?: string; password?: string }) =>
    request<User>("/users/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: { name?: string; phone_number?: string; role?: string; password?: string }) =>
    request<User>(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) =>
    request<{ detail: string }>(`/users/${id}`, { method: "DELETE" }),
};

export interface CallsListParams {
  status?: string;
  manager_id?: number;
  limit?: number;
  offset?: number;
}

export const callsApi = {
  list: (params?: CallsListParams) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.manager_id) searchParams.set("manager_id", String(params.manager_id));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return request<Call[]>(`/calls/${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<CallDetail>(`/calls/${id}`),
  upload: async (file: File, managerId?: number) => {
    const formData = new FormData();
    formData.append("file", file);
    const params = managerId ? `?manager_id=${managerId}` : "";
    const url = `${BASE}/calls/upload${params}`;
    let res = await fetch(url, {
      method: "POST",
      body: formData,
      headers: { ...authHeader() },
    });
    if (res.status === 401) {
      const newToken = await tryRefresh();
      if (newToken) {
        res = await fetch(url, {
          method: "POST",
          body: formData,
          headers: { ...authHeader() },
        });
      } else {
        handleAuthFailure();
        throw new Error("Требуется авторизация");
      }
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ call_id: number; s3_key: string }>;
  },
  analyze: (callId: number) =>
    request<AnalyzeEnqueueResponse>(`/calls/analyze`, {
      method: "POST",
      body: JSON.stringify({ call_id: callId }),
    }),
  delete: (id: number) =>
    request<{ detail: string }>(`/calls/${id}`, { method: "DELETE" }),
};

export interface AnalyzeEnqueueResponse {
  call_id: number;
  task_id: string;
  status: string;
}

export type TaskState =
  | "PENDING"
  | "PROGRESS"
  | "SUCCESS"
  | "FAILURE"
  | "RETRY"
  | "REVOKED";

export interface TaskStatusResponse {
  task_id: string;
  state: TaskState;
  step?: string | null;
  percent?: number | null;
  call_id?: number | null;
  call_status?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
}

export const tasksApi = {
  status: (taskId: string) =>
    request<TaskStatusResponse>(`/tasks/${taskId}/status`),
};

export interface CheckCreateData {
  name: string;
  description?: string;
  scope?: string;
  type?: string;
  output_type?: string;
  weight?: number;
  active?: boolean;
  rule_config?: Record<string, unknown>;
  prompt?: string;
  expected_format?: string;
}

export const checksApi = {
  list: (params?: { scope?: string; type?: string; active?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.scope) searchParams.set("scope", params.scope);
    if (params?.type) searchParams.set("type", params.type);
    if (params?.active !== undefined) searchParams.set("active", String(params.active));
    const qs = searchParams.toString();
    return request<Check[]>(`/checks/${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<Check>(`/checks/${id}`),
  create: (data: CheckCreateData) =>
    request<Check>("/checks/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<CheckCreateData>) =>
    request<Check>(`/checks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) =>
    request<{ detail: string }>(`/checks/${id}`, { method: "DELETE" }),
};

export interface ManagerStatsResponse {
  manager_id: number;
  manager_name: string;
  total_calls: number;
  analyzed_calls: number;
  error_calls: number;
  avg_duration: number;
  analyze_rate: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  check_pass_rate: number | null;
  avg_score: number | null;
}

export interface CheckStatsResponse {
  check_id: number;
  name: string;
  type: string;
  output_type: string;
  active: boolean;
  total_runs: number;
  passed: number;
  failed: number;
  pass_rate: number | null;
  avg_score: number | null;
}

export const analyticsApi = {
  managerStats: () => request<ManagerStatsResponse[]>("/analytics/manager-stats"),
  checkStats: () => request<CheckStatsResponse[]>("/analytics/check-stats"),
};

export interface IntegrationLogsParams {
  status?: string;
  provider?: string;
  limit?: number;
  offset?: number;
}

export const integrationsApi = {
  status: () => request<IntegrationStatus>("/integrations/status"),
  listLogs: (params?: IntegrationLogsParams) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.provider) searchParams.set("provider", params.provider);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return request<IntegrationLog[]>(`/integrations/logs${qs ? `?${qs}` : ""}`);
  },
};

export function getAudioUrl(audioId: string): string {
  const token = authStorage.getAccess();
  const qs = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${BASE}/calls/audio/${audioId}${qs}`;
}
