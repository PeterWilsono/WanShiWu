<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout(): Promise<void> {
  authStore.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <main class="home">
    <h1>万事屋</h1>
    <p class="home__sub">个人生活效率平台</p>
    <p v-if="authStore.user" class="home__welcome">你好，{{ authStore.user.username }}</p>
    <el-button class="home__logout" @click="handleLogout">退出登录</el-button>
  </main>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  gap: 8px;
}

.home__sub {
  color: #909399;
  margin: 0;
}

.home__welcome {
  margin-top: 16px;
}

.home__logout {
  margin-top: 8px;
}
</style>
