import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development, API calls to /api are proxied to the Flask backend so the app
// works even when VITE_API_URL is empty. Set VITE_API_URL to call a remote API.
const target = process.env.VITE_PROXY_TARGET || 'http://localhost:5000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target, changeOrigin: true },
      '/health': { target, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom', 'react-redux', '@reduxjs/toolkit'],
          'vendor-charts': ['recharts'],
          'vendor-ui': ['framer-motion', 'lucide-react', 'react-hot-toast', 'react-dropzone', 'react-hook-form', 'date-fns'],
        },
      },
    },
  },
});
