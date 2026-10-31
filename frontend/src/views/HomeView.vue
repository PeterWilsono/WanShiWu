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
    <div class="home__actions">
      <el-button type="primary" @click="router.push({ name: 'todos' })">管理待办</el-button>
      <el-button type="primary" plain @click="router.push({ name: 'events' })">管理日程</el-button>
      <el-button type="success" plain @click="router.push({ name: 'transactions' })">管理账目</el-button>
      <el-button type="warning" plain @click="router.push({ name: 'stats' })">月度统计</el-button>
      <el-button @click="router.push({ name: 'categories' })">分类管理</el-button>
      <el-button @click="handleLogout">退出登录</el-button>
    </div>
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

.home__actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.home__actions .el-button + .el-button {
  margin-left: 0;
}
</style>
