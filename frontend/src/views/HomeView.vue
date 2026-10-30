<script setup lang="ts">
// 首页（阶段 0 占位）：全局输入框、四个模块入口、今日概览在后续阶段实现（PROJECT_SPEC.md 3.1）
</script>

<template>
  <main class="home">
    <h1>万事屋</h1>
    <p class="home__sub">个人生活效率平台</p>
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
</style>
