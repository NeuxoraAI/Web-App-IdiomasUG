// Backend API client. The session token lives in sessionStorage so a page
// reload keeps the exam going (the timer runs on the server).

import { API_URL } from './config.js';

const KEY = 'exaubi-token';

function storage(fn) {
  try { return fn(sessionStorage); } catch { return null; }
}

export const getToken = () => storage((s) => s.getItem(KEY));
export const setToken = (t) => storage((s) => (t ? s.setItem(KEY, t) : s.removeItem(KEY)));

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function api(method, path, body) {
  let res;
  try {
    res = await fetch(API_URL + path, {
      method,
      headers: {
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(getToken() && { Authorization: `Bearer ${getToken()}` }),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.');
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Ocurrió un error; inténtalo de nuevo.';
    throw new ApiError(res.status, detail);
  }
  return data;
}
