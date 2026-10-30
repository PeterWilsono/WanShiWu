<script setup lang="ts">
import { computed } from 'vue'

import type { TransactionType } from '../types/category'
import { formatTransactionMoney } from '../utils/money'

const props = defineProps<{
  amountCents: number
  type: TransactionType
}>()

const text = computed(() => formatTransactionMoney(props.amountCents, props.type))
</script>

<template>
  <span class="money" :class="`money--${type}`">{{ text }}</span>
</template>

<style scoped>
.money {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  white-space: nowrap;
}

.money--income {
  color: #28956f;
}

.money--expense {
  color: #303133;
}
</style>
