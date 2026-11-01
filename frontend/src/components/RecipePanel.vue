<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'

import { addRecipeMissingToShopping, cookRecipe, recommendRecipes } from '../api/pantry'
import { ApiError } from '../api/http'
import type { Recipe } from '../types/pantry'
import { formatQuantity } from '../utils/quantity'
import AppIcon from './AppIcon.vue'

const emit = defineEmits<{ cooked: []; shoppingAdded: [] }>()
const preferences = ref('')
const servings = ref(2)
const recipes = ref<Recipe[]>([])
const loading = ref(false)
const errorMessage = ref('')
const cooking = ref<Recipe | null>(null)
const adding = ref<Recipe | null>(null)
const added = ref<Recipe[]>([])

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function recommend(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  recipes.value = []
  added.value = []
  try {
    recipes.value = await recommendRecipes({
      preferences: preferences.value.trim() || undefined,
      servings: servings.value,
    })
  } catch (error) {
    errorMessage.value = messageOf(error, '菜谱推荐失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function cook(recipe: Recipe): Promise<void> {
  if (recipe.missing.length || !recipe.uses.length || cooking.value) return
  cooking.value = recipe
  try {
    const result = await cookRecipe({ recipe_name: recipe.name, uses: recipe.uses })
    const remaining = result.consumed
      .map((item) => `${item.name}剩 ${formatQuantity(item.remaining_stock)}${item.unit}`)
      .join('，')
    ElMessage.success(`已扣减库存${remaining ? `：${remaining}` : ''}`)
    recipes.value = recipes.value.filter((item) => item !== recipe)
    emit('cooked')
  } catch (error) {
    ElMessage.error(messageOf(error, '库存扣减失败，请核对库存后重试'))
  } finally {
    cooking.value = null
  }
}

async function addMissing(recipe: Recipe): Promise<void> {
  if (!recipe.missing.length || adding.value || added.value.includes(recipe)) return
  adding.value = recipe
  try {
    const result = await addRecipeMissingToShopping({
      recipe_name: recipe.name,
      missing: recipe.missing,
    })
    added.value.push(recipe)
    ElMessage.success(`已把 ${result.items.length} 项缺料加入购物清单`)
    emit('shoppingAdded')
  } catch (error) {
    ElMessage.error(messageOf(error, '加入购物清单失败'))
  } finally {
    adding.value = null
  }
}
</script>

<template>
  <section class="recipe-panel">
    <div class="recipe-intro">
      <div>
        <p class="recipe-kicker">从现有食材出发</p>
        <h2>今天，做一顿刚好的饭</h2>
        <p>优先参考临期食材；库存与缺料由服务端重新核算。</p>
      </div>
      <AppIcon name="food" :size="38" :stroke-width="1.2" />
    </div>

    <form class="recipe-controls" @submit.prevent="recommend">
      <el-input
        v-model="preferences"
        maxlength="200"
        placeholder="口味偏好（可选），例如：清淡、少油、不吃辣"
        aria-label="口味偏好"
      />
      <el-input-number v-model="servings" :min="1" :max="12" aria-label="用餐人数" />
      <span class="servings-label">人份</span>
      <el-button type="primary" native-type="submit" :loading="loading">
        {{ loading ? '正在搭配…' : '推荐三道菜' }}
      </el-button>
    </form>
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false">
      <el-button size="small" @click="recommend">重新推荐</el-button>
    </el-alert>

    <section v-loading="loading" class="recipe-results" aria-live="polite">
      <div v-if="!recipes.length && !loading && !errorMessage" class="recipe-empty">
        <AppIcon name="sparkle" :size="28" />
        <h3>让库存先决定菜单</h3>
        <p>写下偏好和人数，AI 会给出三道候选；确认做菜后才会扣减库存。</p>
      </div>
      <template v-else>
        <p v-if="recipes.length" class="ai-notice">AI 生成，请自行核实食材状态、用量与烹饪安全。</p>
        <div class="recipe-grid">
          <article v-for="recipe in recipes" :key="recipe.name" class="recipe-card">
            <header>
              <div><span class="recipe-number">家常菜谱</span><h3>{{ recipe.name }}</h3></div>
              <span class="recipe-time"><AppIcon name="clock" :size="15" />{{ recipe.minutes }} 分钟</span>
            </header>
            <div class="ingredient-lines">
              <section>
                <h4>现有食材</h4>
                <p v-if="!recipe.uses.length" class="muted">暂无匹配库存</p>
                <ul><li v-for="item in recipe.uses" :key="`${item.name}-${item.unit}`">
                  <span>{{ item.name }}</span><strong>{{ formatQuantity(item.quantity) }}{{ item.unit }}</strong>
                </li></ul>
              </section>
              <section v-if="recipe.missing.length" class="missing-lines">
                <h4>还需补购</h4>
                <ul><li v-for="item in recipe.missing" :key="`${item.name}-${item.unit}`">
                  <span>{{ item.name }}</span><strong>{{ formatQuantity(item.quantity) }}{{ item.unit }}</strong>
                </li></ul>
              </section>
            </div>
            <details class="recipe-steps">
              <summary>查看做法 <span>{{ recipe.steps.length }} 步</span></summary>
              <ol><li v-for="step in recipe.steps" :key="step">{{ step }}</li></ol>
            </details>
            <p v-if="recipe.missing.length" class="cook-hint">补齐缺料并录入库存后，可重新推荐再确认做菜。</p>
            <footer>
              <el-button
                size="small" :disabled="!recipe.missing.length || added.includes(recipe)"
                :loading="adding === recipe" @click="addMissing(recipe)"
              >{{ added.includes(recipe) ? '已加入清单' : '把缺的加入购物清单' }}</el-button>
              <el-button
                size="small" type="primary" :disabled="!!recipe.missing.length || !recipe.uses.length"
                :loading="cooking === recipe" @click="cook(recipe)"
              >做了这道菜</el-button>
            </footer>
          </article>
        </div>
      </template>
    </section>
  </section>
</template>

<style scoped>
.recipe-panel { padding-top: 24px; }
.recipe-intro { display: flex; align-items: center; justify-content: space-between; margin-bottom: 26px; color: var(--ink); }
.recipe-kicker { margin-bottom: 8px; color: var(--vermilion); font-size: 11px; letter-spacing: .16em; }
.recipe-intro h2 { margin-bottom: 8px; font-family: var(--font-display); font-size: 28px; font-weight: 600; }
.recipe-intro p:last-child { color: var(--ink-muted); font-size: 13px; line-height: 1.7; }
.recipe-intro > svg { margin-right: 12px; color: var(--gold); }
.recipe-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.recipe-controls .el-input { flex: 1; }
.recipe-controls .el-input-number { width: 120px; }
.servings-label { margin-left: -8px; color: var(--ink-muted); font-size: 12px; }
.recipe-results { min-height: 250px; }
.recipe-empty { padding: 55px 20px; border: 1px dashed var(--line); text-align: center; }
.recipe-empty svg { color: var(--gold); }
.recipe-empty h3 { margin: 14px 0 8px; font-family: var(--font-display); font-size: 22px; }
.recipe-empty p, .muted { color: var(--ink-muted); font-size: 13px; }
.ai-notice { margin-bottom: 18px; color: var(--ink-muted); font-size: 12px; }
.recipe-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.recipe-card { display: flex; min-width: 0; flex-direction: column; padding: 24px; border: 1px solid var(--line-soft); border-radius: 3px 20px 3px 3px; background: var(--paper-light); box-shadow: var(--shadow-soft); }
.recipe-card header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.recipe-number { color: var(--vermilion); font-size: 10px; letter-spacing: .12em; }
.recipe-card h3 { margin: 7px 0 0; font-family: var(--font-display); font-size: 25px; font-weight: 600; }
.recipe-time { display: flex; align-items: center; flex-shrink: 0; gap: 4px; color: var(--ink-muted); font-size: 11px; }
.ingredient-lines { display: grid; gap: 18px; margin: 26px 0 20px; }
.ingredient-lines h4 { margin-bottom: 9px; color: var(--ink-secondary); font-size: 12px; font-weight: 600; }
.ingredient-lines li { display: flex; justify-content: space-between; gap: 10px; padding: 5px 0; color: var(--ink-secondary); font-size: 13px; }
.ingredient-lines li strong { font-weight: 500; }
.missing-lines { color: var(--vermilion); }
.missing-lines h4, .missing-lines li { color: var(--vermilion); }
.recipe-steps { margin-bottom: 18px; border-top: 1px solid var(--line-soft); padding-top: 14px; }
.recipe-steps summary { display: flex; justify-content: space-between; cursor: pointer; font-size: 12px; }
.recipe-steps summary span, .recipe-steps ol { color: var(--ink-muted); }
.recipe-steps ol { padding-left: 20px; font-size: 12px; line-height: 1.8; }
.recipe-steps li { margin-top: 8px; }
.cook-hint { margin-top: auto; color: var(--ink-muted); font-size: 11px; line-height: 1.6; }
.recipe-card footer { display: flex; gap: 8px; margin-top: auto; padding-top: 18px; }
.recipe-card footer .el-button { flex: 1; margin: 0; }
@media (max-width: 1050px) { .recipe-grid { grid-template-columns: 1fr; } .recipe-card { min-height: 0; } }
@media (max-width: 640px) {
  .recipe-intro > svg { display: none; }
  .recipe-intro h2 { font-size: 25px; }
  .recipe-controls { align-items: stretch; flex-wrap: wrap; }
  .recipe-controls .el-input { flex-basis: 100%; }
  .recipe-controls .el-button { flex: 1; }
  .recipe-card { padding: 20px; }
  .recipe-card footer { flex-direction: column; }
}
</style>
