// Backend API client. The session token lives in sessionStorage so a page
// reload keeps the exam going (the timer runs on the server).

import { API_URL } from '../services/config';

const KEY = 'exaubi-token';

function storage<T>(fn: (s: Storage) => T): T | null {
  try { return fn(sessionStorage); } catch { return null; }
}

export const getToken = () => storage((s) => s.getItem(KEY));
export const setToken = (t: string | null) => storage((s) => (t ? s.setItem(KEY, t) : s.removeItem(KEY)));

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = null>(method: string, path: string, body?: unknown): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      method,
      headers: {
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.');
  }
  if (res.status === 204) return null as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Ocurrió un error; inténtalo de nuevo.';
    throw new ApiError(res.status, detail);
  }
  return data as T;
}
