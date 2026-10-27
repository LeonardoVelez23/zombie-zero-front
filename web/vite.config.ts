import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // MapLibre pesa ~800 KB del total
  build: { chunkSizeWarningLimit: 1000 },
  server: { port: 5173 }
});
