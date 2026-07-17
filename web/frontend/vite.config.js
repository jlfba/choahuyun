import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3112,
    proxy: {
      '/api': 'http://localhost:8066',
      '/audio': 'http://localhost:8066',
    }
  }
})
