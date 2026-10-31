<script setup lang="ts">
import { computed } from 'vue'

import NetworkStatus from './components/NetworkStatus.vue'
import NotificationCenter from './components/NotificationCenter.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const showNotifications = computed(() => authStore.isAuthenticated && authStore.user !== null)
</script>

<template>
  <NetworkStatus />
  <NotificationCenter v-if="showNotifications" />
  <router-view />
</template>
