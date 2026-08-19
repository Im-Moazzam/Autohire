export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

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
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    // The session cookie is httponly and set by the API's origin (:8000),
    // separate from the frontend's (:5173) — without this, /auth/me and
    // every other authenticated call silently looks logged-out.
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  const body = res.status === 204 ? null : await res.json().catch(() => null);

  if (!res.ok) {
    throw new ApiError(
      `Request to ${path} failed with ${res.status}`,
      res.status,
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
  put: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: data !== undefined ? JSON.stringify(data) : undefined,
    }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: data !== undefined ? JSON.stringify(data) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** Every backend error is `ErrorOut` — {code, message, details} — including
 * 422s (main.py's validation_exception_handler normalizes those too). Falls
 * back to a generic message for anything that isn't an ApiError at all
 * (a network failure never reaches the backend, so it has no ErrorOut body). */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong. Try again."): string {
  if (err instanceof ApiError) {
    const body = err.body as { message?: string } | null;
    if (body?.message) return body.message;
  }
  return fallback;
}

export function apiErrorCode(err: unknown): string | undefined {
  if (err instanceof ApiError) {
    const body = err.body as { code?: string } | null;
    return body?.code;
  }
  return undefined;
}
