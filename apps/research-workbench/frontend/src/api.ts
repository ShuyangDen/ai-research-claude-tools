let csrfToken = "";

async function decode<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function bootstrap(): Promise<{ csrf_token: string; week: string }> {
  const result = await decode<{ csrf_token: string; week: string }>(await fetch("/api/bootstrap"));
  csrfToken = result.csrf_token;
  return result;
}

export async function get<T>(path: string): Promise<T> {
  return decode<T>(await fetch(path));
}

export async function mutate<T>(path: string, method: "POST" | "PATCH", body: unknown = {}): Promise<T> {
  return decode<T>(await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-Workbench-CSRF": csrfToken },
    body: JSON.stringify(body),
  }));
}

export async function uploadPdf<T>(paperId: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  return decode<T>(await fetch(`/api/papers/${encodeURIComponent(paperId)}/pdf`, {
    method: "POST",
    headers: { "X-Workbench-CSRF": csrfToken },
    body,
  }));
}

export function sessionSocket(sessionId: string): WebSocket {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${location.host}/api/sessions/${encodeURIComponent(sessionId)}/events`);
}
