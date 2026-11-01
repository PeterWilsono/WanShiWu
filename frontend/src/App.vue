<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from './components/AppHeader.vue'
import NetworkStatus from './components/NetworkStatus.vue'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const showShell = computed(() => authStore.isAuthenticated && authStore.user !== null && route.name !== 'login')
</script>

<template>
  <NetworkStatus />
  <AppHeader v-if="showShell" />
  <router-view v-slot="{ Component, route: currentRoute }">
    <Transition name="page" mode="out-in">
      <component :is="Component" :key="currentRoute.path" />
    </Transition>
  </router-view>
</template>
