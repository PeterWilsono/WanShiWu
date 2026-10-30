<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '../api/http'
import { useAuthStore } from '../stores/auth'
import type { LoginRequest } from '../types/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const form = reactive<LoginRequest>({ username: '', password: '' })
const errorMessage = ref('')

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function redirectTarget(): string {
  const queryValue = route.query.redirect
  const target = Array.isArray(queryValue) ? queryValue[0] : queryValue
  // 只允许站内绝对路径，排除 //example.com 等外部跳转。
  if (target?.startsWith('/') && !target.startsWith('//')) return target
  return '/'
}

async function handleLogin(): Promise<void> {
  errorMessage.value = ''
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  try {
    await authStore.login(form)
    ElMessage.success('登录成功')
    await router.push(redirectTarget())
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '登录失败，请稍后重试'
  }
}
</script>

<template>
  <main class="login-page">
    <el-card class="login-card" shadow="never">
      <div class="login-header">
        <h1>万事屋</h1>
        <p>登录后管理你的生活</p>
      </div>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="false"
        show-icon
        class="login-alert"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            autocomplete="username"
            placeholder="请输入用户名"
            autofocus
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          class="login-button"
          :loading="authStore.loading"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </main>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  border: none;
  border-radius: 12px;
}

.login-header {
  margin-bottom: 28px;
  text-align: center;
}

.login-header h1 {
  margin-bottom: 8px;
  font-size: 30px;
}

.login-header p {
  color: #909399;
}

.login-alert {
  margin-bottom: 20px;
}

.login-button {
  width: 100%;
  margin-top: 8px;
}
</style>
