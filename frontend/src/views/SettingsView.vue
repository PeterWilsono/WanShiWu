<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { ApiError } from '../api/http'
import {
  deleteLLMConfig,
  getSettings,
  testLLMConnection,
  updateGeneralSettings,
  updateLLMConfig,
} from '../api/settings'
import AppIcon from '../components/AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import type { DesktopDataLocation } from '../types/desktop'
import type { AppSettings, GeneralSettings, LLMProvider } from '../types/settings'

interface ProviderForm {
  api_key: string
  base_url: string
  model: string
  is_active: boolean
}

type SettingsTab = 'ai' | 'general' | 'storage'

const route = useRoute()
const authStore = useAuthStore()
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const testing = ref(false)
const savingGeneral = ref(false)
const settings = ref<AppSettings | null>(null)
const desktopBridge = window.wanshiwuDesktop
const isDesktop = Boolean(desktopBridge)
const initialTab = route.query.tab
const requestedTab: SettingsTab =
  initialTab === 'general' ? 'general' : initialTab === 'storage' ? 'storage' : 'ai'
// 浏览器里没有桌面壳，数据位置由服务器决定，不能提供切换入口。
const activeTab = ref<SettingsTab>(requestedTab === 'storage' && !isDesktop ? 'ai' : requestedTab)
const selectedProvider = ref<LLMProvider>('mimo')
const localTestMessage = ref('')
const localTestSuccess = ref(false)
const dataLocation = ref<DesktopDataLocation | null>(null)
const locationLoading = ref(false)
const locationError = ref('')
const switchingLocation = ref(false)
const migrating = ref(false)
const forms = reactive<Record<LLMProvider, ProviderForm>>({
  mimo: { api_key: '', base_url: '', model: '', is_active: false },
  deepseek: { api_key: '', base_url: '', model: '', is_active: false },
})
const general = reactive<GeneralSettings>({
  timezone: 'Asia/Shanghai',
  expiring_days: 3,
  daily_llm_call_limit: 200,
})

const providers = computed(() => settings.value?.providers ?? [])
const currentInfo = computed(() =>
  providers.value.find((provider) => provider.provider === selectedProvider.value) ?? null,
)
const currentForm = computed(() => forms[selectedProvider.value])
const activeProvider = computed(() => providers.value.find((provider) => provider.is_active))

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function syncProvider(provider: LLMProvider): void {
  const info = providers.value.find((item) => item.provider === provider)
  if (!info) return
  forms[provider].base_url = info.base_url
  forms[provider].model = info.model
  forms[provider].is_active = info.is_active
  forms[provider].api_key = ''
}

function syncGeneral(): void {
  if (!settings.value) return
  Object.assign(general, settings.value.general)
}

async function loadSettings(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    settings.value = await getSettings()
    syncProvider('mimo')
    syncProvider('deepseek')
    syncGeneral()
  } catch (error) {
    loadError.value = errorMessage(error, '设置加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function selectProvider(provider: LLMProvider): void {
  selectedProvider.value = provider
  localTestMessage.value = ''
}

function configPayload(): { api_key: string | null; base_url: string; model: string } {
  return {
    api_key: currentForm.value.api_key.trim() || null,
    base_url: currentForm.value.base_url.trim(),
    model: currentForm.value.model.trim(),
  }
}

async function saveConfig(): Promise<void> {
  if (!currentForm.value.model.trim()) {
    ElMessage.warning('请填写模型名称')
    return
  }
  if (currentInfo.value?.source !== 'user' && !currentForm.value.api_key.trim()) {
    ElMessage.warning('首次配置请填写 API Key')
    return
  }
  saving.value = true
  localTestMessage.value = ''
  try {
    settings.value = await updateLLMConfig(selectedProvider.value, {
      ...configPayload(),
      is_active: currentForm.value.is_active,
    })
    syncProvider(selectedProvider.value)
    ElMessage.success(currentForm.value.is_active ? '配置已保存并设为当前模型' : '配置已保存')
  } catch (error) {
    ElMessage.error(errorMessage(error, '模型配置保存失败'))
  } finally {
    saving.value = false
  }
}

async function testConnection(): Promise<void> {
  testing.value = true
  localTestMessage.value = ''
  try {
    const result = await testLLMConnection(selectedProvider.value, configPayload())
    localTestSuccess.value = true
    localTestMessage.value = `${result.message} · ${result.latency_ms} ms`
    ElMessage.success('连接测试成功，请记得保存当前配置')
  } catch (error) {
    localTestSuccess.value = false
    localTestMessage.value = errorMessage(error, '连接测试失败')
  } finally {
    testing.value = false
  }
}

async function removeConfig(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `将删除当前账号保存的 ${currentInfo.value?.label || ''} 配置与密钥，此操作不会影响服务商控制台中的 Key。`,
      '删除模型配置',
      { confirmButtonText: '删除配置', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  saving.value = true
  try {
    settings.value = await deleteLLMConfig(selectedProvider.value)
    syncProvider(selectedProvider.value)
    localTestMessage.value = ''
    ElMessage.success('模型配置已删除')
  } catch (error) {
    ElMessage.error(errorMessage(error, '删除失败'))
  } finally {
    saving.value = false
  }
}

async function saveGeneral(): Promise<void> {
  savingGeneral.value = true
  try {
    const result = await updateGeneralSettings({ ...general })
    Object.assign(general, result)
    if (settings.value) settings.value.general = result
    await authStore.fetchCurrentUser()
    ElMessage.success('通用设置已保存')
  } catch (error) {
    ElMessage.error(errorMessage(error, '通用设置保存失败'))
  } finally {
    savingGeneral.value = false
  }
}

function formatTime(value: string | null): string {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

const sourceLabel = computed(() => {
  switch (dataLocation.value?.source) {
    case 'custom':
      return '自定义位置'
    case 'install':
      return '安装目录内'
    case 'fallback':
      return '系统本地目录'
    case 'pointer-unusable':
      return '临时回退'
    case 'env':
      return '启动参数指定'
    default:
      return '读取中'
  }
})

const onSystemDrive = computed(() => {
  const info = dataLocation.value
  if (!info) return false
  const match = /^([a-z]):/i.exec(info.dataDir)
  if (!match) return false
  return `${match[1].toUpperCase()}:` === (info.systemDrive || 'C:').toUpperCase()
})

function driveName(): string {
  const match = /^([a-z]):/i.exec(dataLocation.value?.dataDir ?? '')
  return match ? `${match[1].toUpperCase()} 盘` : '当前磁盘'
}

async function loadDataLocation(): Promise<void> {
  if (!desktopBridge) return
  locationLoading.value = true
  locationError.value = ''
  try {
    dataLocation.value = await desktopBridge.getDataLocation()
  } catch {
    locationError.value = '读取数据位置失败，请重启软件后再试'
  } finally {
    locationLoading.value = false
  }
}

async function openFolder(kind: 'current' | 'legacy'): Promise<void> {
  if (!desktopBridge) return
  const result = kind === 'current'
    ? await desktopBridge.openDataFolder()
    : await desktopBridge.openLegacyFolder()
  if (!result.ok) ElMessage.error(result.message ? `无法打开文件夹：${result.message}` : '无法打开文件夹')
}

async function chooseFolder(): Promise<void> {
  if (!desktopBridge || switchingLocation.value) return
  try {
    await ElMessageBox.confirm(
      '可以把数据搬到 D 盘等任意位置。迁移会先完整复制并校验，然后自动重启软件；旧位置会保留一份备份，确认新位置正常后可自行删除。',
      '更换数据保存位置',
      { confirmButtonText: '选择新位置', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  switchingLocation.value = true
  try {
    const result = await desktopBridge.chooseDataLocation()
    if (result.restarting) {
      migrating.value = true
      return
    }
    if (!result.ok && !result.canceled) ElMessage.error(result.message || '更换保存位置失败')
  } catch {
    ElMessage.error('更换保存位置失败，请稍后重试')
  } finally {
    switchingLocation.value = false
  }
}

onMounted(() => {
  void loadSettings()
  if (isDesktop) void loadDataLocation()
})
</script>

<template>
  <main class="settings-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">我的万事屋 · 设置</p>
        <h1>偏好设置</h1>
        <p>选择合拍的 AI，也让提醒和日常节奏更适合自己。</p>
      </div>
      <el-button @click="$router.push({ name: 'profile' })">返回我的</el-button>
    </header>

    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false">
      <el-button size="small" @click="loadSettings">重新加载</el-button>
    </el-alert>

    <div v-loading="loading" class="settings-layout">
      <aside class="settings-nav" aria-label="设置分类">
        <button :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">
          <AppIcon name="sparkle" :size="19" /><span><strong>AI 模型</strong><small>MiMo 与 DeepSeek</small></span>
        </button>
        <button :class="{ active: activeTab === 'general' }" @click="activeTab = 'general'">
          <AppIcon name="settings" :size="19" /><span><strong>通用偏好</strong><small>时区、提醒与限额</small></span>
        </button>
        <button v-if="isDesktop" :class="{ active: activeTab === 'storage' }" @click="activeTab = 'storage'">
          <AppIcon name="folder" :size="19" /><span><strong>数据存储</strong><small>保存位置与迁移</small></span>
        </button>
        <button @click="$router.push({ name: 'categories' })">
          <AppIcon name="wallet" :size="19" /><span><strong>分类管理</strong><small>收入与支出分类</small></span>
        </button>
      </aside>

      <section v-if="activeTab === 'ai'" class="settings-content">
        <div class="content-heading">
          <div><p class="page-eyebrow">AI PROVIDER</p><h2>模型服务</h2></div>
          <span v-if="activeProvider" class="active-summary">当前：{{ activeProvider.label }}</span>
          <span v-else class="active-summary inactive">尚未启用</span>
        </div>
        <p class="content-intro">两家配置可以同时保留。密钥仅保存在服务端，页面不会再次显示完整内容。</p>

        <div class="provider-tabs" role="tablist" aria-label="模型服务商">
          <button
            v-for="provider in providers"
            :key="provider.provider"
            role="tab"
            :aria-selected="selectedProvider === provider.provider"
            :class="{ active: selectedProvider === provider.provider }"
            @click="selectProvider(provider.provider)"
          >
            <span class="provider-monogram">{{ provider.provider === 'mimo' ? 'M' : 'D' }}</span>
            <span><strong>{{ provider.label }}</strong><small>{{ provider.configured ? '已配置' : '未配置' }}</small></span>
            <i v-if="provider.is_active">当前</i>
          </button>
        </div>

        <form v-if="currentInfo" class="provider-form" @submit.prevent="saveConfig">
          <div class="provider-title">
            <div><h3>{{ currentInfo.label }}</h3><p>{{ currentInfo.provider === 'mimo' ? '小米 MiMo 开放平台 · OpenAI 兼容接口' : 'DeepSeek 开放平台 · OpenAI 兼容接口' }}</p></div>
            <a :href="currentInfo.console_url" target="_blank" rel="noopener noreferrer">获取 API Key <AppIcon name="arrow" :size="14" /></a>
          </div>

          <el-form label-position="top">
            <el-form-item label="API Key" required>
              <el-input
                v-model="currentForm.api_key"
                type="password"
                show-password
                autocomplete="new-password"
                :placeholder="currentInfo.configured ? `已保存 ${currentInfo.key_hint || '密钥'}，留空表示不修改` : '粘贴服务商控制台创建的 API Key'"
              />
              <p class="field-help">保存后无法查看完整密钥；更换密钥会清除旧的连接测试结果。</p>
            </el-form-item>
            <div class="form-grid">
              <el-form-item label="模型名称" required>
                <el-input v-model="currentForm.model" placeholder="例如 deepseek-flash" />
              </el-form-item>
              <el-form-item label="Base URL" required>
                <el-input v-model="currentForm.base_url" placeholder="服务商官方 HTTPS 地址" />
              </el-form-item>
            </div>
            <el-form-item class="activate-field">
              <el-checkbox v-model="currentForm.is_active">保存后设为我的当前 AI 模型</el-checkbox>
            </el-form-item>
          </el-form>

          <div v-if="currentInfo.last_tested_at && !currentForm.api_key" class="last-test" :class="{ failed: currentInfo.last_test_success === false }">
            <span>{{ currentInfo.last_test_success ? '上次连接成功' : '上次连接失败' }} · {{ formatTime(currentInfo.last_tested_at) }}</span>
            <small v-if="currentInfo.last_test_error">{{ currentInfo.last_test_error }}</small>
          </div>
          <div v-if="localTestMessage" class="test-result" :class="{ failed: !localTestSuccess }" role="status">
            {{ localTestMessage }}
          </div>

          <div class="form-actions">
            <el-button :loading="testing" :disabled="saving" @click="testConnection">测试连接</el-button>
            <el-button type="primary" :loading="saving" :disabled="testing" native-type="submit">保存配置</el-button>
            <el-button v-if="currentInfo.source === 'user'" class="delete-config" text type="danger" :disabled="saving || testing" @click="removeConfig">删除配置</el-button>
          </div>
        </form>

        <el-alert
          title="测试连接会产生一次极小的真实 API 调用。AI 功能还取决于模型是否支持工具调用与 JSON 输出；普通手动功能不受模型配置影响。"
          type="info"
          :closable="false"
          show-icon
          class="settings-note"
        />
      </section>

      <section v-else-if="activeTab === 'general'" class="settings-content">
        <div class="content-heading"><div><p class="page-eyebrow">DAILY PREFERENCES</p><h2>通用偏好</h2></div></div>
        <p class="content-intro">这些选项会作用于对应业务，不需要重启服务。</p>
        <form class="general-form" @submit.prevent="saveGeneral">
          <el-form label-position="top">
            <el-form-item label="所在时区">
              <el-select v-model="general.timezone" filterable allow-create default-first-option>
                <el-option label="中国标准时间（Asia/Shanghai）" value="Asia/Shanghai" />
                <el-option label="协调世界时（UTC）" value="UTC" />
                <el-option label="日本时间（Asia/Tokyo）" value="Asia/Tokyo" />
                <el-option label="伦敦时间（Europe/London）" value="Europe/London" />
                <el-option label="纽约时间（America/New_York）" value="America/New_York" />
              </el-select>
              <p class="field-help">用于提醒、周报和每日限额的自然日计算，请填写有效 IANA 时区。</p>
            </el-form-item>
            <el-form-item label="食材临期提醒天数">
              <el-input-number v-model="general.expiring_days" :min="1" :max="30" />
              <p class="field-help">默认查看未来多少天内到期的食材，范围 1～30 天。</p>
            </el-form-item>
            <el-form-item label="每日 AI 调用上限">
              <el-input-number v-model="general.daily_llm_call_limit" :min="1" :max="10000" />
              <p class="field-help">按当前时区的自然日统计，帮助控制 API 额度消耗。</p>
            </el-form-item>
          </el-form>
          <el-button type="primary" native-type="submit" :loading="savingGeneral">保存通用设置</el-button>
        </form>
      </section>

      <section v-else class="settings-content">
        <div class="content-heading">
          <div><p class="page-eyebrow">LOCAL DATA</p><h2>数据存储</h2></div>
          <span class="active-summary" :class="{ inactive: !dataLocation }">{{ sourceLabel }}</span>
        </div>
        <p class="content-intro">所有记录只保存在这台电脑，不会自动云同步。备份时请先完全退出软件，再复制整个数据文件夹。</p>

        <el-alert v-if="locationError" :title="locationError" type="error" show-icon :closable="false">
          <el-button size="small" @click="loadDataLocation">重新读取</el-button>
        </el-alert>

        <div v-loading="locationLoading" class="storage-card">
          <p class="storage-label">当前保存位置</p>
          <code class="storage-path">{{ dataLocation?.dataDir || '读取中…' }}</code>
          <p class="field-help">{{ dataLocation?.reason || '这里显示软件实际读写数据库的文件夹。' }}</p>
          <div class="storage-actions">
            <el-button :disabled="!dataLocation" @click="openFolder('current')">打开文件夹</el-button>
            <el-button
              type="primary"
              :loading="switchingLocation"
              :disabled="!dataLocation || migrating"
              @click="chooseFolder"
            >
              更换保存位置
            </el-button>
          </div>
        </div>

        <el-alert
          v-if="onSystemDrive"
          class="storage-alert"
          type="warning"
          show-icon
          :closable="false"
          title="数据目前放在系统盘（C 盘）"
          description="可以换到 D 盘等非系统盘，减少 C 盘占用。点击“更换保存位置”选择目标文件夹，软件会自动复制、校验并重启。"
        />

        <div class="storage-facts">
          <div><span>保存规则</span><strong>{{ sourceLabel }}</strong></div>
          <div><span>所在磁盘</span><strong>{{ driveName() }}</strong></div>
          <div><span>运行日志</span><strong class="storage-fact-path">{{ dataLocation?.logFile || '—' }}</strong></div>
          <div><span>位置记录</span><strong class="storage-fact-path">{{ dataLocation?.pointerFile || '—' }}</strong></div>
        </div>

        <div v-if="dataLocation?.legacyHasData" class="storage-note">
          <p><strong>旧位置还留有一份数据副本</strong></p>
          <code class="storage-path">{{ dataLocation?.legacyDir }}</code>
          <p class="field-help">确认新位置数据完整后，可以手动删除这个文件夹，释放系统盘空间。</p>
          <el-button size="small" @click="openFolder('legacy')">打开旧位置</el-button>
        </div>

        <el-alert
          class="storage-alert"
          type="info"
          show-icon
          :closable="false"
          title="关于备份和迁移"
          description="数据文件夹里主要是 wanshiwu.db（数据库）和 jwt-secret.txt（本机登录凭据）。迁移会先复制再校验大小，失败时不会删除原数据。"
        />
      </section>
    </div>

    <div v-if="migrating" class="migrating-overlay" role="status" aria-live="polite">
      <div class="migrating-card">
        <p class="page-eyebrow">MOVING DATA</p>
        <h2>正在迁移数据</h2>
        <p>数据复制并校验完成后，软件会自动重启。请不要强制关闭窗口。</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
.settings-page { width: min(1180px, 100%); margin: 0 auto; padding: 52px 32px 80px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 34px; }
.page-eyebrow { margin: 0 0 8px; color: var(--vermilion); font-size: 10px; font-weight: 700; letter-spacing: .2em; }
.page-header h1 { margin: 0 0 10px; font-family: var(--font-display); font-size: 43px; font-weight: 600; }
.page-header p:last-child, .content-intro { margin: 0; color: var(--ink-muted); font-size: 14px; line-height: 1.7; }
.settings-layout { display: grid; grid-template-columns: 218px minmax(0, 1fr); gap: 42px; min-height: 480px; margin-top: 24px; }
.settings-nav { display: flex; flex-direction: column; gap: 7px; }
.settings-nav button { display: flex; align-items: center; gap: 12px; padding: 15px 14px; border: 1px solid transparent; border-radius: 3px 12px 3px 3px; color: var(--ink-secondary); background: transparent; cursor: pointer; text-align: left; }
.settings-nav button.active { border-color: var(--line-soft); color: var(--ink); background: var(--paper-light); box-shadow: var(--shadow-soft); }
.settings-nav button > span { display: grid; gap: 4px; }
.settings-nav strong { font-size: 14px; font-weight: 600; }
.settings-nav small { color: var(--ink-muted); font-size: 10px; }
.settings-content { min-width: 0; }
.content-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.content-heading h2 { margin: 0; font-family: var(--font-display); font-size: 29px; font-weight: 600; }
.active-summary { padding: 5px 10px; border-radius: 99px; color: var(--pine); background: color-mix(in srgb, var(--pine) 9%, transparent); font-size: 11px; }
.active-summary.inactive { color: var(--ink-muted); background: var(--paper-deep); }
.content-intro { margin: 10px 0 25px; }
.provider-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }
.provider-tabs button { position: relative; display: flex; align-items: center; gap: 12px; padding: 16px; border: 1px solid var(--line-soft); border-radius: 3px 14px 3px 3px; color: var(--ink); background: var(--paper-light); cursor: pointer; text-align: left; }
.provider-tabs button.active { border-color: var(--vermilion); box-shadow: 0 0 0 1px color-mix(in srgb, var(--vermilion) 12%, transparent); }
.provider-monogram { display: grid; width: 38px; height: 38px; flex: 0 0 auto; place-items: center; border-radius: 11px 11px 11px 3px; color: var(--paper-light); background: var(--ink); font-family: var(--font-display); font-size: 19px; }
.provider-tabs button > span:nth-child(2) { display: grid; gap: 4px; }
.provider-tabs strong { font-size: 14px; }
.provider-tabs small { color: var(--ink-muted); font-size: 11px; }
.provider-tabs i { position: absolute; top: 9px; right: 10px; color: var(--vermilion); font-size: 10px; font-style: normal; }
.provider-form, .general-form { padding: 28px; border: 1px solid var(--line-soft); border-radius: 3px 18px 3px 3px; background: var(--paper-light); }
.provider-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 24px; }
.provider-title h3 { margin: 0 0 5px; font-family: var(--font-display); font-size: 21px; }
.provider-title p { margin: 0; color: var(--ink-muted); font-size: 11px; }
.provider-title a { display: flex; align-items: center; gap: 4px; color: var(--vermilion); font-size: 12px; text-decoration: none; white-space: nowrap; }
.form-grid { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); gap: 16px; }
.field-help { margin: 7px 0 0; color: var(--ink-muted); font-size: 11px; line-height: 1.6; }
.activate-field { margin-bottom: 4px; }
.form-actions { display: flex; align-items: center; gap: 10px; margin-top: 22px; }
.form-actions .el-button + .el-button { margin-left: 0; }
.delete-config { margin-left: auto !important; }
.last-test, .test-result { display: grid; gap: 4px; margin-top: 14px; padding: 10px 12px; border-radius: 3px 9px 3px 3px; color: var(--pine); background: color-mix(in srgb, var(--pine) 8%, transparent); font-size: 12px; }
.last-test.failed, .test-result.failed { color: var(--vermilion); background: color-mix(in srgb, var(--vermilion) 7%, transparent); }
.last-test small { font-size: 11px; }
.settings-note { margin-top: 18px; background: color-mix(in srgb, var(--paper-light) 70%, transparent); }
.general-form { max-width: 580px; }
.general-form :deep(.el-select), .general-form :deep(.el-input-number) { width: 100%; }
.storage-card { padding: 24px; border: 1px solid var(--line-soft); border-radius: 3px 18px 3px 3px; background: var(--paper-light); }
.storage-label { margin: 0 0 9px; color: var(--ink-muted); font-size: 11px; letter-spacing: .08em; }
.storage-path { display: block; padding: 10px 12px; border: 1px dashed var(--line-soft); border-radius: 3px 9px 3px 3px; color: var(--ink); background: var(--paper-deep); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; line-height: 1.6; word-break: break-all; }
.storage-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.storage-actions .el-button + .el-button { margin-left: 0; }
.storage-alert { margin-top: 16px; }
.storage-facts { margin-top: 18px; overflow: hidden; border: 1px solid var(--line-soft); border-radius: 3px 14px 3px 3px; background: var(--paper-light); }
.storage-facts > div { display: grid; grid-template-columns: 88px minmax(0, 1fr); gap: 12px; padding: 12px 18px; border-bottom: 1px solid var(--line-soft); font-size: 12.5px; }
.storage-facts > div:last-child { border-bottom: none; }
.storage-facts span { color: var(--ink-muted); }
.storage-facts strong { color: var(--ink); font-weight: 500; word-break: break-all; }
.storage-fact-path { font-family: ui-monospace, Consolas, monospace; font-size: 11.5px; }
.storage-note { margin-top: 16px; padding: 18px; border: 1px solid var(--line-soft); border-radius: 3px 14px 3px 3px; background: var(--paper-light); }
.storage-note p { margin: 0 0 9px; color: var(--ink-secondary); font-size: 12.5px; line-height: 1.6; }
.storage-note .storage-path { margin-bottom: 9px; }
.migrating-overlay { position: fixed; inset: 0; z-index: 3000; display: grid; padding: 24px; place-items: center; background: color-mix(in srgb, var(--paper) 82%, transparent); backdrop-filter: blur(3px); }
.migrating-card { max-width: 430px; padding: 30px 28px; border: 1px solid var(--line-soft); border-radius: 3px 18px 3px 3px; background: var(--paper-light); box-shadow: var(--shadow-soft); }
.migrating-card h2 { margin: 0 0 10px; font-family: var(--font-display); font-size: 24px; }
.migrating-card p:last-child { margin: 0; color: var(--ink-muted); font-size: 13px; line-height: 1.7; }
@media (max-width: 800px) {
  .settings-page { padding: 36px 20px 60px; }
  .settings-layout { grid-template-columns: 1fr; gap: 24px; }
  .settings-nav { flex-direction: row; overflow-x: auto; padding-bottom: 5px; }
  .settings-nav button { flex: 0 0 auto; }
  .settings-nav small { display: none; }
}
@media (max-width: 560px) {
  .settings-page { padding: 30px 16px 52px; }
  .page-header h1 { font-size: 36px; }
  .page-header { gap: 12px; }
  .page-header p:last-child { font-size: 12px; }
  .provider-tabs { grid-template-columns: 1fr; }
  .provider-form, .general-form { padding: 21px 17px; }
  .provider-title, .content-heading { align-items: flex-start; }
  .provider-title { flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; gap: 0; }
  .form-actions { flex-wrap: wrap; }
  .delete-config { margin-left: 0 !important; }
}
</style>
