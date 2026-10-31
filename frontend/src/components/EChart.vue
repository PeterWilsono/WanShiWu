<script setup lang="ts">
import { LineChart, PieChart } from 'echarts/charts'
import type { EChartsCoreOption, EChartsType } from 'echarts/core'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { init, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

use([LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  option: EChartsCoreOption
  label: string
}>()

const chartElement = ref<HTMLDivElement | null>(null)
let chart: EChartsType | null = null
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (!chartElement.value) return
  chart = init(chartElement.value)
  chart.setOption(props.option)
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartElement.value)
})

watch(
  () => props.option,
  (option) => chart?.setOption(option, { notMerge: true }),
  { deep: true },
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="chartElement" class="chart" role="img" :aria-label="label" />
</template>

<style scoped>
.chart {
  width: 100%;
  height: 340px;
}
@media (max-width: 700px) {
  .chart { height: 300px; }
}
</style>
