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

registerSW({ immediate: true })
app.mount('#app')
