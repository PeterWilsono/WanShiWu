<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '../api/http'
import AppIcon from '../components/AppIcon.vue'
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
  if (target?.startsWith('/') && !target.startsWith('//')) return target
  return '/'
}

async function handleLogin(): Promise<void> {
  errorMessage.value = ''
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  try {
    await authStore.login(form)
    ElMessage.success('欢迎回来')
    await router.push(redirectTarget())
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '登录失败，请稍后重试'
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-story" aria-label="万事屋介绍">
      <div class="login-story__brand"><span>万</span><strong>万事屋<small>WANSHIWU</small></strong></div>
      <div class="login-story__copy">
        <p class="story-kicker">A QUIET PLACE FOR A FULL LIFE</p>
        <h1>万千小事，<br />都有自己的<em>归处。</em></h1>
        <p>待办、日程、收支与一饭一蔬，<br />在这里，被认真而温柔地照料。</p>
      </div>
      <div class="story-notes" aria-hidden="true">
        <span><AppIcon name="check" :size="17" />把计划轻轻放下</span>
        <span><AppIcon name="calendar" :size="17" />给时间留些余地</span>
        <span><AppIcon name="sparkle" :size="17" />让日常自有秩序</span>
      </div>
      <div class="story-orbit" aria-hidden="true"><i /><i /><b>万</b></div>
      <footer>YOUR PERSONAL LIFE ATELIER <span>EST. 2026</span></footer>
    </section>

    <section class="login-form-section">
      <div class="login-form-wrap">
        <p class="login-form__eyebrow">WELCOME BACK</p>
        <h2>欢迎回来</h2>
        <p class="login-form__intro">今天，也从照顾好一件小事开始。</p>
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon class="login-alert" />
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="handleLogin">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" autocomplete="username" placeholder="你的用户名" autofocus />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" autocomplete="current-password" placeholder="你的密码" show-password />
          </el-form-item>
          <el-button type="primary" native-type="submit" class="login-button" :loading="authStore.loading">
            回到我的生活 <AppIcon name="arrow" :size="17" />
          </el-button>
        </el-form>
        <p class="login-form__privacy"><span />你的个人数据，仅属于你自己</p>
      </div>
      <p class="login-form__foot">LESS NOISE. MORE LIFE.</p>
    </section>
  </main>
</template>

<style scoped>
.login-page { display: grid; min-height: 100vh; grid-template-columns: 1.15fr .85fr; background: var(--paper-light); }
.login-story { position: relative; display: flex; min-height: 100vh; flex-direction: column; overflow: hidden; padding: 44px 6%; color: #f7f2e8; background: var(--ink); }
.login-story::before { position: absolute; inset: 0; background: radial-gradient(circle at 80% 30%, rgb(163 182 149 / 15%), transparent 40%); content: ''; }
.login-story__brand { position: relative; z-index: 2; display: flex; align-items: center; gap: 13px; }
.login-story__brand > span { display: grid; width: 40px; height: 40px; place-items: center; border-radius: 11px 11px 11px 3px; background: var(--vermilion); font-family: var(--font-display); font-size: 24px; transform: rotate(-4deg); }
.login-story__brand strong { display: grid; font-family: var(--font-display); font-size: 20px; letter-spacing: .14em; }
.login-story__brand small { margin-top: 2px; color: rgb(247 242 232 / 45%); font-family: var(--font-body); font-size: 7px; letter-spacing: .3em; }
.login-story__copy { position: relative; z-index: 2; margin: auto 0; padding: 60px 0; }
.story-kicker { margin-bottom: 30px; color: #c2cbbd; font-size: 9px; font-weight: 600; letter-spacing: .26em; }
.login-story h1 { font-family: var(--font-display); font-size: clamp(44px, 5vw, 72px); font-weight: 500; line-height: 1.45; letter-spacing: -.06em; }
.login-story h1 em { color: #d9ab7e; font-style: normal; }
.login-story__copy > p:last-child { margin-top: 28px; color: rgb(247 242 232 / 62%); font-size: 14px; line-height: 2; }
.story-notes { position: relative; z-index: 2; display: flex; flex-wrap: wrap; gap: 22px; padding-bottom: 42px; }
.story-notes span { display: flex; align-items: center; gap: 8px; color: rgb(247 242 232 / 68%); font-size: 11px; }
.login-story footer { position: relative; z-index: 2; display: flex; justify-content: space-between; padding-top: 22px; border-top: 1px solid rgb(247 242 232 / 12%); color: rgb(247 242 232 / 35%); font-size: 8px; letter-spacing: .2em; }
.story-orbit { position: absolute; right: -120px; bottom: 3%; width: 390px; height: 390px; border: 1px solid rgb(247 242 232 / 7%); border-radius: 50%; }
.story-orbit i { position: absolute; inset: 14%; border: 1px solid rgb(247 242 232 / 8%); border-radius: 50%; }
.story-orbit i:nth-child(2) { inset: 29%; }
.story-orbit b { position: absolute; top: 35%; left: 10%; color: rgb(247 242 232 / 5%); font-family: var(--font-display); font-size: 180px; font-weight: 400; }
.login-form-section { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 12%; }
.login-form-wrap { width: min(100%, 400px); animation: login-in .8s both; }
.login-form__eyebrow { margin-bottom: 18px; color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .25em; }
.login-form-wrap h2 { font-family: var(--font-display); font-size: 38px; font-weight: 600; letter-spacing: -.04em; }
.login-form__intro { margin: 13px 0 40px; color: var(--ink-muted); font-size: 13px; }
.login-alert { margin-bottom: 22px; }
.login-form-wrap :deep(.el-form-item) { margin-bottom: 24px; }
.login-form-wrap :deep(.el-input__wrapper) { min-height: 50px; background: var(--paper); }
.login-button { display: flex; width: 100%; min-height: 50px; align-items: center; justify-content: center; gap: 10px; margin-top: 12px; border-radius: 12px; }
.login-form__privacy { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 24px; color: var(--ink-muted); font-size: 11px; }
.login-form__privacy span { width: 5px; height: 5px; border-radius: 50%; background: var(--sage); }
.login-form__foot { margin-top: 80px; color: var(--ink-muted); font-size: 8px; letter-spacing: .26em; }
@keyframes login-in { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 900px) {
  .login-page { grid-template-columns: 1fr; }
  .login-story { min-height: auto; padding: 28px 28px 70px; }
  .login-story__copy { padding: 70px 0 30px; }
  .login-story h1 { font-size: clamp(40px, 9vw, 58px); }
  .story-notes { padding-bottom: 0; }
  .login-story footer { display: none; }
  .story-orbit { right: -170px; bottom: -40px; }
  .login-form-section { min-height: 570px; padding: 64px 24px 30px; }
  .login-form__foot { margin-top: 60px; }
}
@media (max-width: 480px) {
  .login-story { padding: 24px 22px 44px; }
  .login-story__copy { padding-top: 54px; }
  .story-kicker { font-size: 8px; }
  .story-notes { display: grid; gap: 13px; }
  .login-form-section { min-height: 540px; padding-top: 54px; }
}
</style>
