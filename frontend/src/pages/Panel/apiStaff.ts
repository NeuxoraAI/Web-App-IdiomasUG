// API calls with the staff token. A 401 means the staff session expired: the
// Panel listens for SESSION_EXPIRED and goes back to its login.

import { api, ApiError, KEY_PERSONAL } from '../../api/client';

export const SESSION_EXPIRED = 'panel:session-expired';

export function apiStaff<T = null>(method: string, path: string, body?: unknown): Promise<T> {
  return api<T>(method, path, body, KEY_PERSONAL).catch((err: ApiError) => {
    if (err.status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED));
    throw err;
  });
}
