export type IngredientUnit = '个' | '克' | '千克' | '毫升' | '升' | '包' | '瓶'
export type Storage = 'fridge' | 'freezer' | 'room'
export type IngredientStatus = 'active' | 'used_up' | 'discarded'
export type ShoppingSource = 'manual' | 'recipe'

export interface Ingredient {
  id: number
  name: string
  quantity: string
  unit: IngredientUnit
  expire_on: string | null
  purchased_on: string | null
  storage: Storage
  status: IngredientStatus
  note: string | null
  created_at: string
  updated_at: string
}

export interface IngredientPayload {
  name: string
  quantity: string
  unit: IngredientUnit
  expire_on: string | null
  purchased_on: string | null
  storage: Storage
  note: string | null
}

export interface IngredientListQuery {
  page?: number
  page_size?: number
  status?: IngredientStatus
  storage?: Storage
  name?: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ConsumeBatch {
  ingredient_id: number
  consumed_quantity: string
  remaining_quantity: string
  status: IngredientStatus
}

export interface ConsumeResult {
  name: string
  unit: IngredientUnit
  consumed_quantity: string
  remaining_stock: string
  batches: ConsumeBatch[]
}

export interface ExpiringIngredient extends Ingredient {
  days_to_expire: number
}

export interface ExpiringResult {
  today: string
  days: number
  expired: ExpiringIngredient[]
  expiring: ExpiringIngredient[]
}

export interface ShoppingItem {
  id: number
  name: string
  quantity: string | null
  unit: IngredientUnit | null
  done: boolean
  source: ShoppingSource
  recipe_name: string | null
  created_at: string
  updated_at: string
}

export interface ShoppingItemPayload {
  name: string
  quantity: string | null
  unit: IngredientUnit | null
  source: ShoppingSource
  recipe_name: string | null
}

export interface ShoppingListQuery {
  page?: number
  page_size?: number
  done?: boolean
  source?: ShoppingSource
}

export interface RecipeIngredient {
  name: string
  quantity: string
  unit: IngredientUnit
}

export interface Recipe {
  name: string
  minutes: number
  uses: RecipeIngredient[]
  missing: RecipeIngredient[]
  steps: string[]
}

export interface RecipeRecommendRequest {
  preferences?: string
  servings: number
}

export interface RecipeRecommendResponse {
  recipes: Recipe[]
  inventory_empty: boolean
}

export interface CookRequest {
  recipe_name: string
  uses: RecipeIngredient[]
}

export interface CookResult {
  recipe_name: string
  consumed: ConsumeResult[]
}

export interface RecipeShoppingResult {
  items: ShoppingItem[]
}
