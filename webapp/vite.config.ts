import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          vendor: ['three', 'zustand', 'lucide-react'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: ['goliath'],
    port: 11017,
    proxy: {
      '/api': 'http://127.0.0.1:11016',
      '/sse': 'http://127.0.0.1:11016',
      '/mcp': 'http://127.0.0.1:11016',
    },
  },
});
