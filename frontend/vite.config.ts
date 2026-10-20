import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Dev only: the API runs separately on :8000 (Caddy proxies /api in production)
  server: { proxy: { '/api': 'http://localhost:8000' } },
});
