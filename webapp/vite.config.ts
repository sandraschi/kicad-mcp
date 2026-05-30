import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['goliath'],
    port: 11017,
    proxy: {
      '/api': 'http://127.0.0.1:11016',
      '/sse': 'http://127.0.0.1:11016',
      '/mcp': 'http://127.0.0.1:11016',
    },
  },
});
