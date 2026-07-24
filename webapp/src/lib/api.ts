export const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '' : 'http://127.0.0.1:11016');

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiPost(path: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiUpload(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/v1/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
