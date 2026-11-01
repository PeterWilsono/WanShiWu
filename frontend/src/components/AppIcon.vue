<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number; strokeWidth?: number }>(), {
  size: 20,
  strokeWidth: 1.7,
})
</script>

<template>
  <svg
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'home'"><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-6h6v6"/></template>
    <template v-else-if="name === 'check'"><rect x="3" y="3" width="18" height="18" rx="5"/><path d="m8 12 2.5 2.5L16 9"/></template>
    <template v-else-if="name === 'calendar'"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4m8-4v4M3 10h18M8 14h.01m4 0h.01m4 0h.01M8 17h.01m4 0h.01"/></template>
    <template v-else-if="name === 'wallet'"><path d="M4 6.5h14a2 2 0 0 1 2 2V19H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12v3.5"/><path d="M15 11h6v5h-6a2.5 2.5 0 0 1 0-5Z"/><path d="M15.5 13.5h.01"/></template>
    <template v-else-if="name === 'chart'"><path d="M4 20V10m6 10V4m6 16v-7m5 7H2"/></template>
    <template v-else-if="name === 'pantry'"><path d="M6 3h12l1 5v12H5V8l1-5Z"/><path d="M5 8h14M9 12h6M9 16h4"/></template>
    <template v-else-if="name === 'bookmark'"><path d="M6 3h12v18l-6-4-6 4V3Z"/><path d="M9 7h6M9 11h4"/></template>
    <template v-else-if="name === 'bell'"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/></template>
    <template v-else-if="name === 'arrow'"><path d="M5 12h14m-5-5 5 5-5 5"/></template>
    <template v-else-if="name === 'sparkle'"><path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4L12 3Z"/><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z"/></template>
    <template v-else-if="name === 'settings'"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></template>
    <template v-else-if="name === 'logout'"><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5m5-4 4-4-4-4m4 4H9"/></template>
    <template v-else-if="name === 'plus'"><path d="M12 5v14M5 12h14"/></template>
    <template v-else-if="name === 'clock'"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></template>
    <template v-else-if="name === 'food'"><path d="M7 3v8m-3-8v5a3 3 0 0 0 6 0V3M7 11v10M16 3c-2 3-2 7 1 9v9m0-18c3 2 4 6 0 9"/></template>
    <template v-else-if="name === 'transport'"><path d="M5 17h14l-1-9H6l-1 9Z"/><path d="M7 8l2-4h6l2 4M4 17v3h3v-3m10 0v3h3v-3M7 13h.01M17 13h.01"/></template>
    <template v-else-if="name === 'shopping'"><path d="M5 8h14l-1 13H6L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/></template>
    <template v-else-if="name === 'entertainment'"><circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4V8Z"/></template>
    <template v-else-if="name === 'medical'"><path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3Z"/></template>
    <template v-else-if="name === 'study'"><path d="M3 5c4-1 7 0 9 2v14c-2-2-5-3-9-2V5Zm18 0c-4-1-7 0-9 2v14c2-2 5-3 9-2V5Z"/></template>
    <template v-else-if="name === 'salary'"><circle cx="12" cy="12" r="9"/><path d="M8 8h8M8 12h8M12 8v10m-3-6 3 3 3-3"/></template>
    <template v-else><circle cx="12" cy="12" r="9"/></template>
  </svg>
</template>
