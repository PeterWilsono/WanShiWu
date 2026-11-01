import { http } from './http'
import type { ApiResponse } from '../types/api'
import type {
  ConsumeResult,
  CookRequest,
  CookResult,
  ExpiringResult,
  Ingredient,
  IngredientListQuery,
  IngredientPayload,
  IngredientUnit,
  Page,
  Recipe,
  RecipeIngredient,
  RecipeRecommendRequest,
  RecipeShoppingResult,
  ShoppingItem,
  ShoppingItemPayload,
  ShoppingListQuery,
} from '../types/pantry'

export async function listIngredients(params: IngredientListQuery): Promise<Page<Ingredient>> {
  const response = await http.get<ApiResponse<Page<Ingredient>>>('/ingredients', { params })
  return response.data.data
}

export async function createIngredient(data: IngredientPayload): Promise<Ingredient> {
  const response = await http.post<ApiResponse<Ingredient>>('/ingredients', data)
  return response.data.data
}

export async function updateIngredient(
  id: number,
  data: Partial<IngredientPayload>,
): Promise<Ingredient> {
  const response = await http.patch<ApiResponse<Ingredient>>(`/ingredients/${id}`, data)
  return response.data.data
}

export async function deleteIngredient(id: number): Promise<void> {
  await http.delete(`/ingredients/${id}`)
}

export async function consumeIngredient(data: {
  name: string
  quantity: string
  unit: IngredientUnit
}): Promise<ConsumeResult> {
  const response = await http.post<ApiResponse<ConsumeResult>>('/ingredients/consume', data)
  return response.data.data
}

export async function recommendRecipes(data: RecipeRecommendRequest): Promise<Recipe[]> {
  const response = await http.post<ApiResponse<{ recipes: Recipe[] }>>(
    '/pantry/recipes',
    data,
    { timeout: 100_000 },
  )
  return response.data.data.recipes
}

export async function cookRecipe(data: CookRequest): Promise<CookResult> {
  const response = await http.post<ApiResponse<CookResult>>('/pantry/cook', data)
  return response.data.data
}

export async function addRecipeMissingToShopping(data: {
  recipe_name: string
  missing: RecipeIngredient[]
}): Promise<RecipeShoppingResult> {
  const response = await http.post<ApiResponse<RecipeShoppingResult>>(
    '/pantry/recipes/shopping-items',
    data,
  )
  return response.data.data
}

export async function listExpiring(days?: number): Promise<ExpiringResult> {
  const response = await http.get<ApiResponse<ExpiringResult>>('/ingredients/expiring', {
    params: days === undefined ? {} : { days },
  })
  return response.data.data
}

export async function listShoppingItems(params: ShoppingListQuery): Promise<Page<ShoppingItem>> {
  const response = await http.get<ApiResponse<Page<ShoppingItem>>>('/shopping-items', { params })
  return response.data.data
}

export async function createShoppingItem(data: ShoppingItemPayload): Promise<ShoppingItem> {
  const response = await http.post<ApiResponse<ShoppingItem>>('/shopping-items', data)
  return response.data.data
}

export async function updateShoppingItem(
  id: number,
  data: Partial<ShoppingItemPayload> & { done?: boolean },
): Promise<ShoppingItem> {
  const response = await http.patch<ApiResponse<ShoppingItem>>(`/shopping-items/${id}`, data)
  return response.data.data
}

export async function deleteShoppingItem(id: number): Promise<void> {
  await http.delete(`/shopping-items/${id}`)
}
