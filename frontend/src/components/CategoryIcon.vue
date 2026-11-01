<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from './AppIcon.vue'

const props = withDefaults(defineProps<{ icon: string | null; name: string; size?: number }>(), {
  size: 22,
})
const knownIcons = new Set([
  'food', 'transport', 'shopping', 'home', 'entertainment', 'medical', 'study', 'salary', 'other',
])
const hasVectorIcon = computed(() => props.icon !== null && knownIcons.has(props.icon))
const fallback = computed(() => {
  const value = props.icon?.trim()
  if (value) return Array.from(value).slice(0, 2).join('')
  return Array.from(props.name.trim())[0] || '账'
})
</script>

<template>
  <AppIcon v-if="hasVectorIcon" :name="icon!" :size="size" />
  <span v-else class="category-icon__fallback">{{ fallback }}</span>
</template>

<style scoped>
.category-icon__fallback { display: block; max-width: 100%; overflow: hidden; font-family: var(--font-display); font-size: 15px; line-height: 1; text-overflow: ellipsis; white-space: nowrap; }
</style>
