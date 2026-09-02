let csrfToken = "";

type BootstrapResult = { csrf_token: string; week: string };

export function paperSegment(paperId: string): string {
  const bytes = new TextEncoder().encode(paperId);
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return `~${btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")}`;
}

async function decode<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function bootstrap(): Promise<BootstrapResult> {
  const result = await decode<BootstrapResult>(await fetch("/api/bootstrap", { cache: "no-store" }));
  csrfToken = result.csrf_token;
  return result;
}

export async function get<T>(path: string): Promise<T> {
  return decode<T>(await fetch(path, { cache: "no-store" }));
}

async function fetchWithCsrf(path: string, init: RequestInit): Promise<Response> {
  const send = () => {
    const headers = new Headers(init.headers);
    headers.set("X-Workbench-CSRF", csrfToken);
    return fetch(path, { ...init, headers });
  };
  let response = await send();
  if (response.status !== 403) return response;
  const payload = await response.clone().json().catch(() => ({})) as { detail?: string };
  if (payload.detail !== "Missing or invalid CSRF token.") return response;
  await bootstrap();
  response = await send();
  return response;
}

export async function mutate<T>(path: string, method: "POST" | "PATCH", body: unknown = {}): Promise<T> {
  return decode<T>(await fetchWithCsrf(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }));
}

export async function uploadPdf<T>(paperId: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  return decode<T>(await fetchWithCsrf(`/api/papers/${paperSegment(paperId)}/pdf`, {
    method: "POST",
    body,
  }));
}

export async function uploadProjectImage<T>(slug: string, file: File, caption = ""): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  if (caption) body.append("caption", caption);
  return decode<T>(await fetchWithCsrf(`/api/projects/${encodeURIComponent(slug)}/notes/image`, {
    method: "POST",
    body,
  }));
}

export function sessionSocket(sessionId: string): WebSocket {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${location.host}/api/sessions/${encodeURIComponent(sessionId)}/events`);
}
