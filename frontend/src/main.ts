import { createPinia } from 'pinia'
import { registerSW } from 'virtual:pwa-register'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// 桌面版页面由本机后端直接提供，禁用 PWA 缓存，避免重启时旧 Service Worker 拦截页面。
if (!/Electron/i.test(navigator.userAgent)) {
  registerSW({ immediate: true })
}
app.mount('#app')
