<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  consumeIngredient,
  createIngredient,
  createShoppingItem,
  deleteIngredient,
  deleteShoppingItem,
  listExpiring,
  listIngredients,
  listShoppingItems,
  updateIngredient,
  updateShoppingItem,
} from '../api/pantry'
import { ApiError } from '../api/http'
import RecipePanel from '../components/RecipePanel.vue'
import type {
  ExpiringResult,
  Ingredient,
  IngredientPayload,
  IngredientUnit,
  ShoppingItem,
  ShoppingItemPayload,
  Storage,
} from '../types/pantry'
import { formatQuantity } from '../utils/quantity'

const units: IngredientUnit[] = ['个', '克', '千克', '毫升', '升', '包', '瓶']
const storageOptions: { value: Storage; label: string }[] = [
  { value: 'fridge', label: '冷藏' },
  { value: 'freezer', label: '冷冻' },
  { value: 'room', label: '常温' },
]
const activeTab = ref('inventory')
const ingredients = ref<Ingredient[]>([])
const inventoryTotal = ref(0)
const availableInventoryTotal = ref<number | null>(null)
const inventoryPage = ref(1)
const inventoryPageSize = 20
const storageFilter = ref<Storage | ''>('')
const inventoryLoading = ref(false)
const inventoryError = ref('')
const expiring = ref<ExpiringResult>({ today: '', days: 3, expired: [], expiring: [] })
const expiringDays = ref(3)
const expiringLoading = ref(false)
const expiringError = ref('')
const shoppingItems = ref<ShoppingItem[]>([])
const shoppingTotal = ref(0)
const shoppingPage = ref(1)
const shoppingPageSize = 20
const shoppingLoading = ref(false)
const shoppingError = ref('')
const saving = ref(false)
const actionId = ref<number | null>(null)

const ingredientDialog = ref(false)
const editingIngredient = ref<Ingredient | null>(null)
const ingredientForm = reactive<IngredientPayload>(emptyIngredient())
const consumeDialog = ref(false)
const consumeSource = ref<Ingredient | null>(null)
const consumeQuantity = ref('')
const shoppingDialog = ref(false)
const editingShopping = ref<ShoppingItem | null>(null)
const shoppingForm = reactive<ShoppingItemPayload>(emptyShopping())

const groupedIngredients = computed(() =>
  storageOptions
    .map((storage) => ({
      ...storage,
      items: ingredients.value.filter((item) => item.storage === storage.value),
    }))
    .filter((group) => group.items.length > 0),
)

function emptyIngredient(): IngredientPayload {
  return {
    name: '',
    quantity: '',
    unit: '个',
    expire_on: null,
    purchased_on: null,
    storage: 'fridge',
    note: null,
  }
}

function emptyShopping(): ShoppingItemPayload {
  return { name: '', quantity: null, unit: null, source: 'manual', recipe_name: null }
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function loadInventory(): Promise<void> {
  inventoryLoading.value = true
  inventoryError.value = ''
  try {
    const [result, availability] = await Promise.all([
      listIngredients({
        page: inventoryPage.value,
        page_size: inventoryPageSize,
        status: 'active',
        storage: storageFilter.value || undefined,
      }),
      listIngredients({ page: 1, page_size: 1, status: 'active' }),
    ])
    ingredients.value = result.items
    inventoryTotal.value = result.total
    availableInventoryTotal.value = availability.total
  } catch (error) {
    inventoryError.value = messageOf(error, '库存加载失败，请稍后重试')
  } finally {
    inventoryLoading.value = false
  }
}

async function loadExpiring(): Promise<void> {
  expiringLoading.value = true
  expiringError.value = ''
  try {
    expiring.value = await listExpiring(expiringDays.value)
  } catch (error) {
    expiringError.value = messageOf(error, '临期食材加载失败')
  } finally {
    expiringLoading.value = false
  }
}

async function loadShopping(): Promise<void> {
  shoppingLoading.value = true
  shoppingError.value = ''
  try {
    const result = await listShoppingItems({
      page: shoppingPage.value,
      page_size: shoppingPageSize,
    })
    shoppingItems.value = result.items
    shoppingTotal.value = result.total
  } catch (error) {
    shoppingError.value = messageOf(error, '购物清单加载失败')
  } finally {
    shoppingLoading.value = false
  }
}

function applyStorageFilter(): void {
  inventoryPage.value = 1
  void loadInventory()
}

function openIngredient(item?: Ingredient): void {
  editingIngredient.value = item ?? null
  Object.assign(
    ingredientForm,
    item
      ? {
          name: item.name,
          quantity: item.quantity,
          unit: item.unit,
          expire_on: item.expire_on,
          purchased_on: item.purchased_on,
          storage: item.storage,
          note: item.note,
        }
      : emptyIngredient(),
  )
  ingredientDialog.value = true
}

async function saveIngredient(): Promise<void> {
  if (!ingredientForm.name.trim() || Number(ingredientForm.quantity) <= 0) {
    ElMessage.warning('请填写食材名称和大于 0 的数量')
    return
  }
  saving.value = true
  try {
    const payload = { ...ingredientForm, name: ingredientForm.name.trim() }
    if (editingIngredient.value) {
      await updateIngredient(editingIngredient.value.id, payload)
    } else {
      await createIngredient(payload)
    }
    ElMessage.success(editingIngredient.value ? '食材已更新' : '食材已入库')
    ingredientDialog.value = false
    await Promise.all([loadInventory(), loadExpiring()])
  } catch (error) {
    ElMessage.error(messageOf(error, '保存食材失败'))
  } finally {
    saving.value = false
  }
}

async function removeIngredient(item: Ingredient): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除批次“${item.name}”吗？`, '删除食材批次', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  actionId.value = item.id
  try {
    await deleteIngredient(item.id)
    if (ingredients.value.length === 1 && inventoryPage.value > 1) inventoryPage.value -= 1
    ElMessage.success('食材批次已删除')
    await Promise.all([loadInventory(), loadExpiring()])
  } catch (error) {
    ElMessage.error(messageOf(error, '删除失败'))
  } finally {
    actionId.value = null
  }
}

function openConsume(item: Ingredient): void {
  consumeSource.value = item
  consumeQuantity.value = ''
  consumeDialog.value = true
}

async function saveConsume(): Promise<void> {
  const source = consumeSource.value
  if (!source || Number(consumeQuantity.value) <= 0) {
    ElMessage.warning('请输入大于 0 的消耗数量')
    return
  }
  saving.value = true
  try {
    const result = await consumeIngredient({
      name: source.name,
      unit: source.unit,
      quantity: consumeQuantity.value,
    })
    ElMessage.success(`已扣减 ${formatQuantity(result.consumed_quantity)}${result.unit}，剩余 ${formatQuantity(result.remaining_stock)}${result.unit}`)
    consumeDialog.value = false
    await Promise.all([loadInventory(), loadExpiring()])
  } catch (error) {
    ElMessage.error(messageOf(error, '扣减失败'))
  } finally {
    saving.value = false
  }
}

function expiryLabel(days: number): string {
  if (days < 0) return `已过期 ${-days} 天`
  if (days === 0) return '今天到期'
  return `${days} 天后到期`
}

function openShopping(item?: ShoppingItem): void {
  editingShopping.value = item ?? null
  Object.assign(
    shoppingForm,
    item
      ? {
          name: item.name,
          quantity: item.quantity,
          unit: item.unit,
          source: item.source,
          recipe_name: item.recipe_name,
        }
      : emptyShopping(),
  )
  shoppingDialog.value = true
}

async function saveShopping(): Promise<void> {
  if (!shoppingForm.name.trim()) {
    ElMessage.warning('请填写购物项名称')
    return
  }
  if (shoppingForm.quantity && Number(shoppingForm.quantity) <= 0) {
    ElMessage.warning('数量必须大于 0，也可以留空')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...shoppingForm,
      name: shoppingForm.name.trim(),
      quantity: shoppingForm.quantity || null,
    }
    if (editingShopping.value) {
      await updateShoppingItem(editingShopping.value.id, payload)
    } else {
      await createShoppingItem(payload)
    }
    ElMessage.success(editingShopping.value ? '购物项已更新' : '已加入购物清单')
    shoppingDialog.value = false
    await loadShopping()
  } catch (error) {
    ElMessage.error(messageOf(error, '保存购物项失败'))
  } finally {
    saving.value = false
  }
}

async function toggleShopping(item: ShoppingItem): Promise<void> {
  actionId.value = item.id
  try {
    await updateShoppingItem(item.id, { done: item.done })
    ElMessage.success(item.done ? '已标记完成' : '已恢复为待购买')
  } catch (error) {
    item.done = !item.done
    ElMessage.error(messageOf(error, '状态更新失败'))
  } finally {
    actionId.value = null
  }
}

async function removeShopping(item: ShoppingItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除“${item.name}”吗？`, '删除购物项', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  actionId.value = item.id
  try {
    await deleteShoppingItem(item.id)
    if (shoppingItems.value.length === 1 && shoppingPage.value > 1) shoppingPage.value -= 1
    ElMessage.success('购物项已删除')
    await loadShopping()
  } catch (error) {
    ElMessage.error(messageOf(error, '删除失败'))
  } finally {
    actionId.value = null
  }
}

function handleRecipeCooked(): void {
  void Promise.all([loadInventory(), loadExpiring()])
}

function handleShoppingAdded(): void {
  void loadShopping()
}

onMounted(() => {
  void loadInventory()
  void loadExpiring()
  void loadShopping()
})
</script>

<template>
  <main class="pantry-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">食材管家</p>
        <h1>库存与购物清单</h1>
        <p class="page-subtitle">按批次管理保质期，消耗时自动先扣最早过期的食材。</p>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="pantry-tabs">
      <el-tab-pane label="库存" name="inventory">
        <div class="toolbar">
          <el-select v-model="storageFilter" placeholder="全部存放方式" clearable @change="applyStorageFilter">
            <el-option v-for="item in storageOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button type="primary" @click="openIngredient()">食材入库</el-button>
        </div>
        <el-alert v-if="inventoryError" :title="inventoryError" type="error" show-icon :closable="false">
          <el-button size="small" @click="loadInventory">重新加载</el-button>
        </el-alert>
        <section v-loading="inventoryLoading" class="tab-content">
          <el-empty v-if="!inventoryLoading && !ingredients.length && !inventoryError" description="暂无库存">
            <el-button type="primary" @click="openIngredient()">录入第一批食材</el-button>
          </el-empty>
          <div v-for="group in groupedIngredients" :key="group.value" class="storage-group">
            <h2>{{ group.label }} <span>{{ group.items.length }} 个批次</span></h2>
            <div class="ingredient-grid">
              <el-card v-for="item in group.items" :key="item.id" shadow="never" class="ingredient-card">
                <div class="ingredient-title">
                  <strong>{{ item.name }}</strong>
                  <el-tag v-if="item.expire_on" size="small" type="warning">{{ item.expire_on }} 到期</el-tag>
                  <el-tag v-else size="small" type="info">无保质期</el-tag>
                </div>
                <p class="ingredient-quantity">{{ formatQuantity(item.quantity) }} <small>{{ item.unit }}</small></p>
                <p class="ingredient-meta">购买日：{{ item.purchased_on || '未记录' }}</p>
                <p v-if="item.note" class="ingredient-note">{{ item.note }}</p>
                <div class="card-actions">
                  <el-button size="small" type="primary" plain @click="openConsume(item)">消耗</el-button>
                  <el-button size="small" @click="openIngredient(item)">编辑</el-button>
                  <el-button size="small" type="danger" plain :loading="actionId === item.id" @click="removeIngredient(item)">删除</el-button>
                </div>
              </el-card>
            </div>
          </div>
          <el-pagination
            v-if="inventoryTotal > inventoryPageSize"
            v-model:current-page="inventoryPage"
            :page-size="inventoryPageSize"
            :total="inventoryTotal"
            layout="total, prev, pager, next"
            class="pagination"
            @current-change="loadInventory"
          />
        </section>
      </el-tab-pane>

      <el-tab-pane label="临期" name="expiring">
        <div class="toolbar">
          <span>查看未来</span>
          <el-input-number v-model="expiringDays" :min="0" :max="365" controls-position="right" />
          <span>天及已过期食材</span>
          <el-button @click="loadExpiring">刷新</el-button>
        </div>
        <el-alert v-if="expiringError" :title="expiringError" type="error" show-icon :closable="false" />
        <section v-loading="expiringLoading" class="tab-content">
          <div class="expiry-section expired-section">
            <h2>已过期（{{ expiring.expired.length }}）</h2>
            <el-table v-if="expiring.expired.length" :data="expiring.expired">
              <el-table-column prop="name" label="食材" min-width="120" />
              <el-table-column label="剩余" min-width="110"><template #default="{ row }">{{ formatQuantity(row.quantity) }}{{ row.unit }}</template></el-table-column>
              <el-table-column prop="expire_on" label="过期日" min-width="120" />
              <el-table-column min-width="130"><template #default="{ row }"><el-tag type="danger">{{ expiryLabel(row.days_to_expire) }}</el-tag></template></el-table-column>
            </el-table>
            <p v-else class="empty-line">没有已过期的 active 批次</p>
          </div>
          <div class="expiry-section expiring-section">
            <h2>即将到期（{{ expiring.expiring.length }}）</h2>
            <el-table v-if="expiring.expiring.length" :data="expiring.expiring">
              <el-table-column prop="name" label="食材" min-width="120" />
              <el-table-column label="剩余" min-width="110"><template #default="{ row }">{{ formatQuantity(row.quantity) }}{{ row.unit }}</template></el-table-column>
              <el-table-column prop="expire_on" label="过期日" min-width="120" />
              <el-table-column min-width="130"><template #default="{ row }"><el-tag type="warning">{{ expiryLabel(row.days_to_expire) }}</el-tag></template></el-table-column>
            </el-table>
            <p v-else class="empty-line">这个时间范围内没有临期食材</p>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="购物清单" name="shopping">
        <div class="toolbar toolbar--right">
          <el-button type="primary" @click="openShopping()">添加购物项</el-button>
        </div>
        <el-alert v-if="shoppingError" :title="shoppingError" type="error" show-icon :closable="false">
          <el-button size="small" @click="loadShopping">重新加载</el-button>
        </el-alert>
        <section v-loading="shoppingLoading" class="tab-content">
          <el-empty v-if="!shoppingLoading && !shoppingItems.length && !shoppingError" description="购物清单为空">
            <el-button type="primary" @click="openShopping()">添加第一项</el-button>
          </el-empty>
          <el-table v-else :data="shoppingItems">
            <el-table-column width="70" label="完成">
              <template #default="{ row }"><el-checkbox v-model="row.done" :disabled="actionId === row.id" @change="toggleShopping(row)" /></template>
            </el-table-column>
            <el-table-column min-width="150" label="物品">
              <template #default="{ row }"><span :class="{ 'item-done': row.done }">{{ row.name }}</span></template>
            </el-table-column>
            <el-table-column min-width="110" label="数量"><template #default="{ row }">{{ row.quantity ? `${formatQuantity(row.quantity)}${row.unit || ''}` : '未填写' }}</template></el-table-column>
            <el-table-column min-width="140" label="来源"><template #default="{ row }">{{ row.source === 'recipe' ? `菜谱：${row.recipe_name || '未命名'}` : '手动添加' }}</template></el-table-column>
            <el-table-column width="150" label="操作" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openShopping(row)">编辑</el-button>
                <el-button size="small" type="danger" plain :loading="actionId === row.id" @click="removeShopping(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="shoppingTotal > shoppingPageSize"
            v-model:current-page="shoppingPage"
            :page-size="shoppingPageSize"
            :total="shoppingTotal"
            layout="total, prev, pager, next"
            class="pagination"
            @current-change="loadShopping"
          />
        </section>
      </el-tab-pane>

      <el-tab-pane label="AI 菜谱" name="recipes">
        <RecipePanel
          :inventory-total="availableInventoryTotal"
          @cooked="handleRecipeCooked"
          @shopping-added="handleShoppingAdded"
          @add-ingredient="openIngredient()"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ingredientDialog" :title="editingIngredient ? '编辑食材批次' : '食材入库'" width="min(540px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="名称" required><el-input v-model="ingredientForm.name" maxlength="50" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="数量" required><el-input v-model="ingredientForm.quantity" placeholder="例如 1.5" /></el-form-item>
          <el-form-item label="单位" required><el-select v-model="ingredientForm.unit"><el-option v-for="unit in units" :key="unit" :label="unit" :value="unit" /></el-select></el-form-item>
          <el-form-item label="过期日期"><el-date-picker v-model="ingredientForm.expire_on" type="date" value-format="YYYY-MM-DD" placeholder="可不填" /></el-form-item>
          <el-form-item label="购买日期"><el-date-picker v-model="ingredientForm.purchased_on" type="date" value-format="YYYY-MM-DD" placeholder="可不填" /></el-form-item>
        </div>
        <el-form-item label="存放方式"><el-radio-group v-model="ingredientForm.storage"><el-radio-button v-for="item in storageOptions" :key="item.value" :label="item.value">{{ item.label }}</el-radio-button></el-radio-group></el-form-item>
        <el-form-item label="备注"><el-input v-model="ingredientForm.note" type="textarea" maxlength="200" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="ingredientDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveIngredient">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="consumeDialog" title="消耗食材" width="min(440px, 92vw)">
      <template v-if="consumeSource">
        <el-alert title="系统会按 FEFO 扣减同名同单位的所有批次，最早过期的优先。" type="info" :closable="false" />
        <el-form label-position="top" class="consume-form">
          <el-form-item label="食材"><el-input :model-value="`${consumeSource.name}（${consumeSource.unit}）`" disabled /></el-form-item>
          <el-form-item label="消耗数量" required><el-input v-model="consumeQuantity" placeholder="请输入大于 0 的数量" /></el-form-item>
        </el-form>
      </template>
      <template #footer><el-button @click="consumeDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveConsume">确认扣减</el-button></template>
    </el-dialog>

    <el-dialog v-model="shoppingDialog" :title="editingShopping ? '编辑购物项' : '添加购物项'" width="min(480px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="名称" required><el-input v-model="shoppingForm.name" maxlength="50" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="数量（可留空）"><el-input v-model="shoppingForm.quantity" placeholder="例如 2" /></el-form-item>
          <el-form-item label="单位"><el-select v-model="shoppingForm.unit" clearable><el-option v-for="unit in units" :key="unit" :label="unit" :value="unit" /></el-select></el-form-item>
        </div>
        <el-alert v-if="shoppingForm.source === 'recipe'" :title="`来源菜谱：${shoppingForm.recipe_name || '未命名'}`" type="info" :closable="false" />
      </el-form>
      <template #footer><el-button @click="shoppingDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveShopping">保存</el-button></template>
    </el-dialog>
  </main>
</template>

<style scoped>
.pantry-page { width: min(1180px, 100%); margin: 0 auto; padding: 40px 24px 56px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 24px; }
.page-eyebrow { margin-bottom: 6px; color: #67c23a; font-size: 13px; font-weight: 600; }
.page-header h1 { margin-bottom: 8px; font-size: 32px; }
.page-subtitle { margin: 0; color: #909399; line-height: 1.6; }
.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
.toolbar .el-select { width: 180px; }
.toolbar--right { justify-content: flex-end; }
.tab-content { min-height: 220px; }
.storage-group { margin-bottom: 28px; }
.storage-group h2, .expiry-section h2 { margin-bottom: 14px; font-size: 19px; }
.storage-group h2 span { color: #909399; font-size: 13px; font-weight: 400; }
.ingredient-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.ingredient-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ingredient-title strong { font-size: 17px; }
.ingredient-quantity { margin: 20px 0 10px; color: #303133; font-size: 30px; font-weight: 600; }
.ingredient-quantity small { font-size: 15px; font-weight: 400; }
.ingredient-meta, .ingredient-note { color: #909399; font-size: 13px; }
.ingredient-note { overflow-wrap: anywhere; }
.card-actions { display: flex; margin-top: 18px; }
.card-actions .el-button { flex: 1; }
.expiry-section { margin-bottom: 24px; padding: 20px; border: 1px solid #ebeef5; border-radius: 10px; }
.expired-section { border-left: 4px solid #f56c6c; }
.expiring-section { border-left: 4px solid #e6a23c; }
.empty-line { margin: 0; color: #909399; }
.item-done { color: #a8abb2; text-decoration: line-through; }
.pagination { justify-content: flex-end; margin-top: 24px; }
.el-alert { margin-bottom: 16px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.form-grid .el-select, .form-grid .el-date-editor { width: 100%; }
.consume-form { margin-top: 18px; }
@media (max-width: 900px) { .ingredient-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) {
  .pantry-page { padding: 24px 14px 40px; }
  .page-header { flex-direction: column; }
  .ingredient-grid, .form-grid { grid-template-columns: 1fr; }
  .toolbar .el-select { width: 150px; }
  .pagination { justify-content: center; }
}

/* Editorial refinement */
.pantry-page { width: min(1280px, 100%); padding: 58px 36px 80px; }
.page-header { margin-bottom: 32px; }
.page-header h1 { margin-bottom: 12px; font-size: 44px; }
.page-subtitle { font-size: 14px; }
.pantry-tabs { padding: 0 4px; }
.toolbar { margin: 24px 0; }
.storage-group { margin-bottom: 38px; }
.storage-group h2, .expiry-section h2 { font-family: var(--font-display); font-size: 22px; font-weight: 600; }
.ingredient-grid { gap: 18px; }
.ingredient-card { position: relative; overflow: hidden; border-radius: 3px 20px 3px 3px; transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease; }
.ingredient-card::after { position: absolute; top: -35px; right: -35px; width: 90px; height: 90px; border: 1px solid var(--line); border-radius: 50%; content: ''; opacity: .5; }
.ingredient-card:hover { border-color: var(--line); box-shadow: var(--shadow-lift); transform: translateY(-4px); }
.ingredient-title strong { font-family: var(--font-display); font-size: 20px; }
.ingredient-quantity { margin: 25px 0 12px; color: var(--ink); font-family: var(--font-display); font-size: 36px; font-weight: 500; letter-spacing: -.04em; }
.ingredient-meta, .ingredient-note { color: var(--ink-muted); line-height: 1.7; }
.card-actions { gap: 8px; }
.expiry-section { padding: 24px; border-color: var(--line-soft); border-radius: 3px 20px 3px 3px; background: var(--paper-light); }
.expired-section { border-left: 3px solid var(--danger); }
.expiring-section { border-left: 3px solid var(--gold); }
.empty-line { color: var(--ink-muted); font-size: 13px; }
@media (max-width: 640px) {
  .pantry-page { padding: 38px 18px 60px; }
  .page-header h1 { font-size: 36px; }
  .pantry-tabs { padding: 0; }
  .expiry-section { padding: 16px; }
}
</style>
