export interface Food {
  food_id?: string | null;
  name_en: string;
  name_ar: string;
  carbs: number;
  category_en?: string;
  category_ar?: string;
  serving_description?: string;
  source?: string;
}

export interface FoodResponse {
  success: boolean;
  query: string;
  lang: "en" | "ar";
  results: Food[];
  message: string;
}

export interface APIKey {
  key: string;
  name: string;
  created_at: string;
  is_active: boolean;
}

export interface APIKeyCreate {
  name: string;
}

export interface WorkerRegistration {
  name: string;
  url: string;
}

export interface WorkerInfo {
  name: string;
  url: string;
  status: "active" | "inactive";
  last_heartbeat?: string;
  current_load: number;
  failures?: number;
  registered_at?: string;
}

export interface DBTableInfo {
  name: string;
  row_count: number;
}

export interface DBTableData {
  columns: string[];
  rows: (string | number | null)[][];
  total: number;
  page: number;
  per_page: number;
}

export interface DBSchemaColumn {
  name: string;
  type: string;
  not_null: boolean;
  default: string | null;
}

export interface DBQueryRequest {
  sql: string;
}

export interface DBQueryResult {
  columns: string[];
  rows: (string | number | null)[][];
  row_count: number;
}

export interface CacheStats {
  memory_entries: number;
  db_entries: number;
  total_queries: number;
  cache_hits: number;
  hit_rate: number;
}

export interface ScraperStatus {
  state: "running" | "idle" | "stopped" | "error";
  current_food: string | null;
  foods_scraped: number;
  foods_failed: number;
  total_foods: number;
  batch_number: number;
  last_batch_time: string | null;
  errors: { food?: string; error: string }[];
  started_at: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface CoordinatorHealth {
  status: string;
  mode: string;
  active_workers: number;
  total_workers: number;
}

export const API = {
  BASE: "",
  SEARCH_GET: (q: string) => `/api/foods/search?q=${encodeURIComponent(q)}`,
  SEARCH_POST: "/api/foods/search",
  LIST_FOODS: "/api/foods",
  ADD_FOOD: "/api/foods",
  ADD_FOODS_BULK: "/api/foods/bulk",
  DELETE_FOOD: (id: string) => `/api/foods/${encodeURIComponent(id)}`,
  HEALTH: "/api/health",
  SCRAPER_STATUS: "/api/scraper/status",
  SCRAPER_START: "/api/scraper/start",
  SCRAPER_STOP: "/api/scraper/stop",
  DB_STATS: "/api/db/stats",
  DB_TABLES: "/api/db/tables",
  DB_TABLE_DATA: (name: string, page = 1, perPage = 50) =>
    `/api/db/table/${encodeURIComponent(name)}?page=${page}&per_page=${perPage}`,
  DB_TABLE_SCHEMA: (name: string) => `/api/db/table/${encodeURIComponent(name)}/schema`,
  DB_QUERY: "/api/db/query",
  CACHE_STATS: "/api/cache/stats",
  CACHE_INVALIDATE: "/api/cache/invalidate",
  WORKERS: "/api/workers",
  WORKER_REGISTER: "/api/workers/register",
  WORKER_DEREGISTER: (name: string) => `/api/workers/${encodeURIComponent(name)}`,
  WORKER_HEARTBEAT: (name: string) => `/api/workers/${encodeURIComponent(name)}/heartbeat`,
  WORKER_STATUS: (name: string) => `/api/workers/${encodeURIComponent(name)}/status`,
  COORDINATOR_HEALTH: "/api/coordinator/health",
  WORKER_INFO: "/api/worker/info",
  AUTH_KEY: "/api/auth/key",
  AI_KEYS: "/api/ai-keys",
} as const;

export async function searchFoods(q: string, apiKey?: string): Promise<FoodResponse> {
  const headers: Record<string, string> = {};
  if (apiKey) headers["X-API-Key"] = apiKey;
  const r = await fetch(API.SEARCH_GET(q), { headers });
  return r.json();
}

export async function addFood(food: Food, apiKey: string): Promise<{ success: boolean; message: string }> {
  const r = await fetch(API.ADD_FOOD, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(food),
  });
  return r.json();
}

export async function deleteFood(foodId: string, apiKey: string): Promise<{ success: boolean; message: string }> {
  const r = await fetch(API.DELETE_FOOD(foodId), {
    method: "DELETE",
    headers: { "X-API-Key": apiKey },
  });
  return r.json();
}

export async function listFoods(): Promise<{ success: boolean; count: number; foods: Food[] }> {
  const r = await fetch(API.LIST_FOODS);
  return r.json();
}

export async function getScraperStatus(): Promise<{ success: boolean; scraper: ScraperStatus }> {
  const r = await fetch(API.SCRAPER_STATUS);
  return r.json();
}

export async function runSQLQuery(sql: string): Promise<{ success: boolean } & DBQueryResult> {
  const r = await fetch(API.DB_QUERY, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
  return r.json();
}
