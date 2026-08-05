/** API client with bearer auth + refresh. */

import type {
  AuthStatus,
  CalendarItem,
  CareEvent,
  CareTask,
  Dashboard,
  Household,
  Invitation,
  LayoutSite,
  Member,
  MetaResponse,
  PaginatedPlants,
  Plant,
  PlantPhoto,
  SetupResponse,
  StatsSummary,
  Taxon,
  TokenResponse,
  User,
  WateringInfo,
} from "@/lib/types";

const ACCESS_KEY = "plantpilot_access_token";
const REFRESH_KEY = "plantpilot_refresh_token";
const HOUSEHOLD_KEY = "plantpilot_active_household";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function getActiveHouseholdId(): string | null {
  return localStorage.getItem(HOUSEHOLD_KEY);
}

export function setActiveHouseholdId(id: string | null) {
  if (id) localStorage.setItem(HOUSEHOLD_KEY, id);
  else localStorage.removeItem(HOUSEHOLD_KEY);
}

export function storeTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  headers?: Record<string, string>;
  formData?: FormData;
};

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) {
    clearTokens();
    return false;
  }
  const data = (await response.json()) as TokenResponse;
  storeTokens(data.access_token, data.refresh_token);
  return true;
}

/** Try refresh once; used by auth bootstrap so expired access tokens don't log you out. */
export async function ensureSession(): Promise<boolean> {
  if (getAccessToken()) return true;
  return tryRefresh();
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, headers = {}, formData } = options;

  const doFetch = async () => {
    const reqHeaders: Record<string, string> = {
      Accept: "application/json",
      ...headers,
    };
    if (body !== undefined && !formData) {
      reqHeaders["Content-Type"] = "application/json";
    }
    if (auth) {
      const token = getAccessToken();
      if (token) reqHeaders.Authorization = `Bearer ${token}`;
    }
    let payload: BodyInit | undefined;
    if (formData) payload = formData;
    else if (body !== undefined) payload = JSON.stringify(body);
    return fetch(path, {
      method,
      headers: reqHeaders,
      body: payload,
      credentials: "include",
    });
  };

  let response = await doFetch();

  if (response.status === 401 && auth) {
    if (!refreshPromise) {
      refreshPromise = tryRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    const ok = await refreshPromise;
    if (ok) {
      response = await doFetch();
    }
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const err = (await response.json()) as { detail?: unknown };
      if (typeof err.detail === "string") detail = err.detail;
      else if (Array.isArray(err.detail)) detail = JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  meta: () => apiRequest<MetaResponse>("/api/v1/meta", { auth: false }),
  authStatus: () => apiRequest<AuthStatus>("/api/v1/auth/status", { auth: false }),
  setup: (body: {
    email: string;
    password: string;
    display_name: string;
    household_name: string;
    timezone?: string;
    latitude?: number | null;
    longitude?: number | null;
  }) => apiRequest<SetupResponse>("/api/v1/auth/setup", { method: "POST", body, auth: false }),
  login: (body: { email: string; password: string }) =>
    apiRequest<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { ...body, client: "api" },
      auth: false,
    }),
  register: (body: { email: string; password: string; display_name: string; timezone?: string }) =>
    apiRequest<TokenResponse>("/api/v1/auth/register", { method: "POST", body, auth: false }),
  me: () => apiRequest<User>("/api/v1/auth/me"),
  logout: () =>
    apiRequest<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
      body: { refresh_token: getRefreshToken() },
      auth: false,
    }),
  listHouseholds: () => apiRequest<Household[]>("/api/v1/households"),
  createHousehold: (body: { name: string; timezone?: string }) =>
    apiRequest<Household>("/api/v1/households", { method: "POST", body }),
  updateHousehold: (
    id: string,
    body: {
      name?: string;
      latitude?: number | null;
      longitude?: number | null;
      timezone?: string;
      auto_cover_images?: boolean;
      plantnet_api_key?: string | null;
      weather_provider?: "open_meteo" | "met_norway";
      plant_id_provider?: "plantnet" | "none";
      settings?: Record<string, unknown>;
    },
  ) => apiRequest<Household>(`/api/v1/households/${id}`, { method: "PATCH", body }),
  getHousehold: (id: string) => apiRequest<Household>(`/api/v1/households/${id}`),
  listMembers: (id: string) => apiRequest<Member[]>(`/api/v1/households/${id}/members`),
  createInvitation: (id: string, body: { email?: string; role?: string }) =>
    apiRequest<Invitation>(`/api/v1/households/${id}/invitations`, { method: "POST", body }),
  listInvitations: (id: string) =>
    apiRequest<Invitation[]>(`/api/v1/households/${id}/invitations`),
  acceptInvitation: (token: string) =>
    apiRequest<Household>("/api/v1/invitations/accept", {
      method: "POST",
      body: { token },
    }),
  searchTaxa: (q: string, householdId?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (householdId) params.set("household_id", householdId);
    return apiRequest<Taxon[]>(`/api/v1/taxa?${params.toString()}`);
  },
  catalogTaxa: (
    q: string,
    householdId?: string,
    opts?: { limit?: number; withImages?: boolean },
  ) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (householdId) params.set("household_id", householdId);
    if (opts?.limit) params.set("limit", String(opts.limit));
    if (opts?.withImages === false) params.set("with_images", "false");
    return apiRequest<
      Array<
        Taxon & { preview_url?: string | null; suggested_environment?: string }
      >
    >(`/api/v1/taxa/catalog?${params.toString()}`);
  },
  taxonPreview: (taxonId: string) =>
    apiRequest<{ taxon_id: string; preview_url: string | null }>(
      `/api/v1/taxa/${taxonId}/preview`,
    ),
  importPlants: (
    householdId: string,
    body: { text: string; auto_cover?: boolean; default_environment?: string | null },
  ) =>
    apiRequest<{
      created_count: number;
      created: Array<{
        id: string | null;
        nickname: string;
        taxon: string | null;
        environment: string | null;
      }>;
      errors: Array<{ line: string; error: string }>;
      skipped: Array<{ line: string; reason: string }>;
    }>(`/api/v1/households/${householdId}/plants/import`, {
      method: "POST",
      body,
    }),
  fetchAutoCover: (householdId: string, plantId: string) =>
    apiRequest<Plant>(
      `/api/v1/households/${householdId}/plants/${plantId}/auto-cover`,
      { method: "POST" },
    ),
  searchPlantPhotos: (householdId: string, plantId: string, q?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", "12");
    return apiRequest<{
      query: string;
      results: Array<{
        title: string;
        url: string;
        thumb_url: string;
        source: string;
      }>;
    }>(
      `/api/v1/households/${householdId}/plants/${plantId}/photo-search?${params.toString()}`,
    );
  },
  setCoverFromUrl: (
    householdId: string,
    plantId: string,
    body: { url: string; caption?: string },
  ) =>
    apiRequest<Plant>(
      `/api/v1/households/${householdId}/plants/${plantId}/cover-from-url`,
      { method: "POST", body },
    ),
  listPlants: (
    householdId: string,
    opts?: { q?: string; status?: string; limit?: number; offset?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.q) params.set("q", opts.q);
    if (opts?.status) params.set("status", opts.status);
    if (opts?.limit) params.set("limit", String(opts.limit));
    if (opts?.offset) params.set("offset", String(opts.offset));
    const qs = params.toString();
    return apiRequest<PaginatedPlants>(
      `/api/v1/households/${householdId}/plants${qs ? `?${qs}` : ""}`,
    );
  },
  getPlant: (householdId: string, plantId: string) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants/${plantId}`),
  createPlant: (
    householdId: string,
    body: {
      nickname: string;
      taxon_id?: string | null;
      environment?: string;
      pot_size_liters?: number | null;
      pot_material?: string | null;
      soil_type?: string | null;
      growth_stage?: string | null;
      notes?: string | null;
      tag_names?: string[];
      acquired_at?: string | null;
      last_fertilized_at?: string | null;
      auto_cover_image?: boolean | null;
    },
  ) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants`, {
      method: "POST",
      body,
    }),
  identifyPlant: (householdId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<{
      provider: string;
      candidates: Array<{
        score: number;
        scientific_name: string;
        common_names: string[];
        family?: string;
        genus?: string;
      }>;
    }>(`/api/v1/households/${householdId}/identify`, {
      method: "POST",
      formData: form,
    });
  },
  updatePlant: (householdId: string, plantId: string, body: Record<string, unknown>) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants/${plantId}`, {
      method: "PATCH",
      body,
    }),
  archivePlant: (householdId: string, plantId: string) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants/${plantId}/archive`, {
      method: "POST",
    }),
  restorePlant: (householdId: string, plantId: string) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants/${plantId}/restore`, {
      method: "POST",
    }),
  deletePlant: (householdId: string, plantId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/plants/${plantId}`, {
      method: "DELETE",
    }),
  copyPlant: (householdId: string, plantId: string) =>
    apiRequest<Plant>(`/api/v1/households/${householdId}/plants/${plantId}/copy`, {
      method: "POST",
    }),
  seedDemo: (householdId: string) =>
    apiRequest<{
      site_id: string;
      garden_id: string;
      plants: Array<{ id: string; nickname: string }>;
      message: string;
    }>(`/api/v1/households/${householdId}/demo/seed`, { method: "POST" }),
  clearDemo: (householdId: string) =>
    apiRequest<{
      plants_removed: number;
      sites_removed: number;
      message: string;
    }>(`/api/v1/households/${householdId}/demo`, { method: "DELETE" }),
  listPhotos: (householdId: string, plantId: string) =>
    apiRequest<PlantPhoto[]>(`/api/v1/households/${householdId}/plants/${plantId}/photos`),
  uploadPhoto: (
    householdId: string,
    plantId: string,
    file: File,
    opts?: { caption?: string; setCover?: boolean },
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (opts?.caption) form.append("caption", opts.caption);
    if (opts?.setCover) form.append("set_cover", "true");
    return apiRequest<PlantPhoto>(
      `/api/v1/households/${householdId}/plants/${plantId}/photos`,
      { method: "POST", formData: form },
    );
  },
  setCoverPhoto: (householdId: string, plantId: string, photoId: string) =>
    apiRequest<Plant>(
      `/api/v1/households/${householdId}/plants/${plantId}/photos/${photoId}/cover`,
      { method: "POST" },
    ),
  deletePhoto: (householdId: string, photoId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/photos/${photoId}`, {
      method: "DELETE",
    }),
  dashboard: (householdId: string) =>
    apiRequest<Dashboard>(`/api/v1/households/${householdId}/dashboard`),
  listEvents: (householdId: string, opts?: { type?: string; limit?: number }) => {
    const params = new URLSearchParams();
    if (opts?.type) params.set("type", opts.type);
    if (opts?.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return apiRequest<CareEvent[]>(
      `/api/v1/households/${householdId}/events${qs ? `?${qs}` : ""}`,
    );
  },
  listPlantEvents: (householdId: string, plantId: string) =>
    apiRequest<CareEvent[]>(`/api/v1/households/${householdId}/plants/${plantId}/events`),
  updateEvent: (
    householdId: string,
    eventId: string,
    body: {
      type?: string;
      plant_id?: string | null;
      clear_plant?: boolean;
      occurred_at?: string | null;
      notes?: string | null;
      payload?: Record<string, unknown>;
    },
  ) =>
    apiRequest<CareEvent>(`/api/v1/households/${householdId}/events/${eventId}`, {
      method: "PATCH",
      body,
    }),
  deleteEvent: (householdId: string, eventId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/events/${eventId}`, {
      method: "DELETE",
    }),
  listTasks: (householdId: string, status = "open") =>
    apiRequest<CareTask[]>(
      `/api/v1/households/${householdId}/tasks?status=${encodeURIComponent(status)}`,
    ),
  createTask: (
    householdId: string,
    body: {
      title: string;
      type?: string;
      description?: string;
      due_at?: string | null;
      plant_ids?: string[];
      priority?: string;
    },
  ) =>
    apiRequest<CareTask>(`/api/v1/households/${householdId}/tasks`, {
      method: "POST",
      body,
    }),
  updateTask: (
    householdId: string,
    taskId: string,
    body: {
      title?: string;
      type?: string;
      description?: string | null;
      due_at?: string | null;
      clear_due?: boolean;
      priority?: string;
      status?: string;
    },
  ) =>
    apiRequest<CareTask>(`/api/v1/households/${householdId}/tasks/${taskId}`, {
      method: "PATCH",
      body,
    }),
  completeTask: (householdId: string, taskId: string) =>
    apiRequest<CareTask>(`/api/v1/households/${householdId}/tasks/${taskId}/complete`, {
      method: "POST",
      body: {},
    }),
  bulkWaterAll: (householdId: string, plantIds?: string[]) =>
    apiRequest<{ watered: number; message: string }>(
      `/api/v1/households/${householdId}/bulk/water-all`,
      {
        method: "POST",
        body: plantIds?.length ? { plant_ids: plantIds } : {},
      },
    ),
  bulkCompleteTasks: (householdId: string, taskIds?: string[]) =>
    apiRequest<{ completed: number; message: string }>(
      `/api/v1/households/${householdId}/bulk/complete-tasks`,
      {
        method: "POST",
        body: taskIds?.length ? { task_ids: taskIds } : {},
      },
    ),
  bulkFertilizeDue: (householdId: string) =>
    apiRequest<{ fertilized: number; message: string }>(
      `/api/v1/households/${householdId}/bulk/fertilize-due`,
      { method: "POST", body: {} },
    ),
  deleteTask: (householdId: string, taskId: string, hard = true) =>
    apiRequest<void>(
      `/api/v1/households/${householdId}/tasks/${taskId}?hard=${hard ? "true" : "false"}`,
      { method: "DELETE" },
    ),
  waterPlant: (
    householdId: string,
    plantId: string,
    body?: { amount?: string; notes?: string },
  ) =>
    apiRequest<{ event: CareEvent; watering: WateringInfo }>(
      `/api/v1/households/${householdId}/plants/${plantId}/water`,
      { method: "POST", body: body ?? { amount: "normal" } },
    ),
  getWatering: (householdId: string, plantId: string) =>
    apiRequest<WateringInfo>(`/api/v1/households/${householdId}/plants/${plantId}/watering`),
  wateringFeedback: (
    householdId: string,
    plantId: string,
    rating: "too_dry" | "ok" | "too_wet",
  ) =>
    apiRequest<WateringInfo>(
      `/api/v1/households/${householdId}/plants/${plantId}/watering-feedback`,
      { method: "POST", body: { rating } },
    ),
  getWeather: (householdId: string) =>
    apiRequest<{
      configured: boolean;
      temperature_c?: number | null;
      humidity?: number | null;
      precip_next_24h_mm?: number | null;
      message?: string;
    }>(`/api/v1/households/${householdId}/weather`),
  refreshWeather: (householdId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/households/${householdId}/weather/refresh`, {
      method: "POST",
    }),
  listSites: (householdId: string) =>
    apiRequest<LayoutSite[]>(`/api/v1/households/${householdId}/sites`),
  createSite: (
    householdId: string,
    name: string,
    opts?: {
      default_room?: string | null;
      default_kind?: string;
      length_m?: number | null;
      width_m?: number | null;
    },
  ) =>
    apiRequest<{ id: string; name: string; space_id?: string | null; space_name?: string | null }>(
      `/api/v1/households/${householdId}/sites`,
      {
        method: "POST",
        body: {
          name,
          default_room: opts?.default_room === null ? null : (opts?.default_room ?? "Garden"),
          default_kind: opts?.default_kind ?? "garden",
          length_m: opts?.length_m ?? null,
          width_m: opts?.width_m ?? null,
        },
      },
    ),
  createSpace: (
    householdId: string,
    siteId: string,
    name: string,
    opts?: {
      kind?: string;
      length_m?: number | null;
      width_m?: number | null;
      notes?: string | null;
    },
  ) =>
    apiRequest<{ id: string; name: string; kind: string }>(
      `/api/v1/households/${householdId}/sites/${siteId}/spaces`,
      {
        method: "POST",
        body: {
          name,
          kind: opts?.kind ?? "garden",
          length_m: opts?.length_m ?? null,
          width_m: opts?.width_m ?? null,
          notes: opts?.notes ?? null,
        },
      },
    ),
  updateSpace: (
    householdId: string,
    spaceId: string,
    body: {
      name?: string;
      kind?: string;
      length_m?: number | null;
      width_m?: number | null;
      notes?: string | null;
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/households/${householdId}/spaces/${spaceId}`,
      { method: "PATCH", body },
    ),
  deleteSpace: (householdId: string, spaceId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/spaces/${spaceId}`, {
      method: "DELETE",
    }),
  deleteSite: (householdId: string, siteId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/sites/${siteId}`, {
      method: "DELETE",
    }),
  createContainer: (
    householdId: string,
    spaceId: string,
    body: {
      name: string;
      kind?: string;
      x?: number;
      y?: number;
      width?: number;
      height?: number;
      path_json?: number[][];
      emoji?: string | null;
    },
  ) =>
    apiRequest<{
      id: string;
      name: string;
      kind: string | null;
      emoji?: string | null;
      x: number;
      y: number;
      width: number | null;
      height: number | null;
      path_json?: number[][];
    }>(`/api/v1/households/${householdId}/spaces/${spaceId}/containers`, {
      method: "POST",
      body: { kind: "circle", ...body },
    }),
  updateContainer: (
    householdId: string,
    containerId: string,
    body: {
      name?: string;
      kind?: string;
      x?: number;
      y?: number;
      width?: number;
      height?: number;
      path_json?: number[][];
      emoji?: string | null;
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/households/${householdId}/containers/${containerId}`,
      { method: "PATCH", body },
    ),
  deleteContainer: (householdId: string, containerId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/containers/${containerId}`, {
      method: "DELETE",
    }),
  copyContainer: (householdId: string, containerId: string) =>
    apiRequest<{
      id: string;
      name: string;
      kind: string | null;
      x: number;
      y: number;
      width: number | null;
      height: number | null;
    }>(`/api/v1/households/${householdId}/containers/${containerId}/copy`, {
      method: "POST",
    }),
  putPlacement: (
    householdId: string,
    plantId: string,
    body: { space_id: string; x?: number; y?: number; container_id?: string | null },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/households/${householdId}/plants/${plantId}/placement`,
      { method: "PUT", body },
    ),
  removePlacement: (householdId: string, plantId: string) =>
    apiRequest<void>(`/api/v1/households/${householdId}/plants/${plantId}/placement`, {
      method: "DELETE",
    }),
  unassignedPlants: (householdId: string) =>
    apiRequest<Array<{ id: string; nickname: string }>>(
      `/api/v1/households/${householdId}/layout/unassigned`,
    ),
  statsSummary: (householdId: string) =>
    apiRequest<StatsSummary>(`/api/v1/households/${householdId}/stats/summary`),
  calendar: (householdId: string, from: string, to: string) =>
    apiRequest<CalendarItem[]>(
      `/api/v1/households/${householdId}/calendar?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
    ),
  plantLabelUrl: (householdId: string, plantId: string) =>
    `/api/v1/households/${householdId}/plants/${plantId}/label.pdf`,
  downloadLabelPdf: async (householdId: string, plantId: string) => {
    const token = getAccessToken();
    const res = await fetch(api.plantLabelUrl(householdId, plantId), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, "Label download failed");
    return res.blob();
  },
};
