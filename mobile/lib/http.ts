import { Platform } from "react-native";
import { API_URL } from "./config";
import { bridgeRequest } from "./webviewBridge";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let status: number;
  let body: unknown;

  if (Platform.OS === "web") {
    // A real browser tab already carries the httponly session cookie
    // automatically via credentials: "include" — no bridge needed, this
    // is exactly what frontend/'s own http.ts does.
    const res = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    status = res.status;
    body = res.status === 204 ? null : await res.json().catch(() => null);
  } else {
    // Native: routed through a hidden WebView on the API's origin, whose
    // page-context fetch() carries the httponly cookie the same way a
    // browser tab does — see lib/webviewBridge.tsx for why.
    const result = await bridgeRequest(`/api/v1${path}`, init);
    status = result.status;
    body = result.body;
  }

  if (!(status >= 200 && status < 300)) {
    throw new ApiError(
      `Request to ${path} failed with ${status}`,
      status,
      body,
    );
  }

  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: data !== undefined ? JSON.stringify(data) : undefined,
    }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: data !== undefined ? JSON.stringify(data) : undefined,
    }),
};

export function apiErrorMessage(
  err: unknown,
  fallback = "Something went wrong. Try again.",
): string {
  if (err instanceof ApiError) {
    const body = err.body as { code?: string; message?: string } | null;
    if (body?.code === "REAUTH_REQUIRED") {
      return "Google authorization has expired. Reconnect from the web app to continue.";
    }
    if (body?.message) return body.message;
  }
  return fallback;
}
