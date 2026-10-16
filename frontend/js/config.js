// App configuration

// Backend base URL. Same-origin '/api' when served behind the nginx proxy.
export const API_URL = location.port === '5500' ? 'http://localhost:8000/api' : '/api';

// When true, the primary button becomes "Comprobar". Answer keys no longer
// reach the browser, so feedback can only say "Respuesta registrada".
export const INSTANT_FEEDBACK = false;

// When true, copying exam text replaces the clipboard with an anti-AI notice
export const AI_GUARD = true;
