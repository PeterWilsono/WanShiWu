<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const online = ref(navigator.onLine)

function updateStatus(): void {
  online.value = navigator.onLine
}

onMounted(() => {
  window.addEventListener('online', updateStatus)
  window.addEventListener('offline', updateStatus)
})

onBeforeUnmount(() => {
  window.removeEventListener('online', updateStatus)
  window.removeEventListener('offline', updateStatus)
})
</script>

<template>
  <el-alert
    v-if="!online"
    class="network-status"
    title="当前网络不可用。已打开的内容可继续查看，但保存、同步和 AI 功能需要联网。"
    type="warning"
    show-icon
    :closable="false"
    role="status"
  />
</template>

<style scoped>
.network-status {
  position: fixed;
  z-index: 3100;
  right: 24px;
  bottom: 24px;
  width: min(520px, calc(100vw - 32px));
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper-light);
  box-shadow: var(--shadow-lift);
}
@media (max-width: 700px) {
  .network-status { right: 16px; bottom: 16px; }
}
</style>
