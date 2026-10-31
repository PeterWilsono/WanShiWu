import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'pwa-icon.svg'],
      manifest: {
        name: '万事屋 · 个人生活效率平台',
        short_name: '万事屋',
        description: '统一管理待办、日程、收支与个人事务',
        lang: 'zh-CN',
        theme_color: '#409eff',
        background_color: '#f5f7fa',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: '/pwa-icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
          { src: '/pwa-icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
  server: {
    // 开发期代理：前端 /api 请求转发到本地后端，避免跨域，
    // 也使开发环境无需配置 VITE_API_BASE_URL
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
