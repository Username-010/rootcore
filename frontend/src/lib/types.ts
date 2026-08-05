export type User = {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  locale: string;
  unit_system: string;
  theme: string;
  is_instance_admin: boolean;
  created_at: string;
};

export type Household = {
  id: string;
  name: string;
  slug: string | null;
  timezone: string;
  currency: string;
  latitude: number | null;
  longitude: number | null;
  settings: {
    auto_cover_images?: boolean;
    plantnet_api_key?: string;
    [key: string]: unknown;
  };
  role: "owner" | "admin" | "member" | "viewer" | null;
  created_at: string;
};

export type Member = {
  user_id: string;
  email: string;
  display_name: string;
  role: "owner" | "admin" | "member" | "viewer";
  joined_at: string;
};

export type Invitation = {
  id: string;
  email: string | null;
  role: "owner" | "admin" | "member" | "viewer";
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
  token?: string | null;
  invite_url_path?: string | null;
};

export type MetaResponse = {
  name: string;
  version: string;
  registration_mode: string;
  initialized: boolean;
  features: {
    plantnet: boolean;
    smtp: boolean;
  };
  docs_url: string;
};

export type AuthStatus = {
  initialized: boolean;
  registration_mode: string;
  user_count: number | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
};

export type SetupResponse = TokenResponse & {
  household_id: string;
  household_name: string;
};

export type CareProfile = {
  light: string | null;
  moisture_preference: string | null;
  drought_tolerance: string | null;
  humidity_preference: string | null;
  baseline_interval_days_min: number | null;
  baseline_interval_days_max: number | null;
  water_amount_default: string | null;
  fertilize_notes: string | null;
  soil_notes: string | null;
  toxic_to_pets: boolean | null;
  extra?: {
    bloom_months?: number[];
    fertilize_interval_days?: number;
    repot_every_months?: number;
    default_environment?: string;
    prune_months?: number[];
    prune_season?: string;
    preview_url?: string;
    [key: string]: unknown;
  };
};

export type Taxon = {
  id: string;
  household_id: string | null;
  parent_id: string | null;
  rank: string;
  scientific_name: string;
  authors: string | null;
  common_names: string[];
  family: string | null;
  genus: string | null;
  care_profile: CareProfile | null;
  created_at: string;
};

export type Tag = {
  id: string;
  name: string;
  color: string | null;
};

export type PlantPhoto = {
  id: string;
  plant_id: string;
  caption: string | null;
  taken_at: string | null;
  mime_type: string;
  byte_size: number;
  width: number | null;
  height: number | null;
  thumb_url: string | null;
  display_url: string | null;
  original_url: string | null;
  created_at: string;
  is_cover: boolean;
};

export type Plant = {
  id: string;
  nickname: string;
  status: string;
  environment: string;
  taxon: Taxon | null;
  cover_photo: PlantPhoto | null;
  tags: Tag[];
  pot_size_liters: number | null;
  pot_material?: string | null;
  soil_type?: string | null;
  growth_stage?: string | null;
  estimated_value?: number | null;
  notes?: string | null;
  emoji?: string | null;
  custom_attributes?: Record<string, unknown>;
  acquired_at: string | null;
  deceased_at?: string | null;
  deceased_reason?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at?: string;
};

export type PaginatedPlants = {
  items: Plant[];
  total: number;
  limit: number;
  offset: number;
};

export type CareEvent = {
  id: string;
  household_id: string;
  plant_id: string | null;
  plant_nickname: string | null;
  actor_user_id: string | null;
  actor_name: string | null;
  type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  task_id: string | null;
  created_at: string;
};

export type WateringInfo = {
  plant_id: string;
  next_due_at: string | null;
  urgency: string;
  recommended_amount: string | null;
  confidence: number | null;
  moisture_score: number | null;
  last_watered_at: string | null;
  paused_until: string | null;
  manual_next_due_at: string | null;
  factors: Array<{
    key: string;
    label: string;
    value: string | number;
    unit?: string;
    effect?: string;
    detail?: string | null;
  }>;
  explanation: string | null;
  amount_label?: string | null;
  amount_howto?: string | null;
  amount_ml?: number | null;
  volume_guide?: string | null;
  best_time_of_day?: string | null;
  best_time_label?: string | null;
  best_time_local?: string | null;
  schedule_plain?: string | null;
  weather_note?: string | null;
  interval_days?: number | null;
  advice?: {
    when?: string;
    how_much?: string;
    volume_ml?: number;
    time_of_day?: string;
    time_label?: string;
    interval_days?: number;
    check_soil?: string;
  } | null;
};

export type CareTask = {
  id: string;
  household_id: string;
  title: string;
  description: string | null;
  type: string;
  status: string;
  priority: string;
  due_at: string | null;
  completed_at: string | null;
  completed_by_user_id: string | null;
  assignee_user_id: string | null;
  source: string;
  plant_ids: string[];
  payload: Record<string, unknown>;
  created_at: string;
};

export type DailyWeather = {
  date: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  precip_mm: number | null;
  weather_code: number | null;
  precip_probability_max?: number | null;
};

export type CareBrief = {
  lines: string[];
  water_today: Array<{
    plant_id: string;
    nickname: string;
    emoji?: string | null;
    urgency: string;
    room: string;
    next_due_at: string | null;
    recommended_amount?: string | null;
    amount_label?: string | null;
  }>;
  water_by_zone: Record<string, string[]>;
  upcoming: Array<{
    plant_id: string;
    nickname: string;
    kind: string;
    room: string;
    at: string | null;
  }>;
  prune: Array<{ task_id: string; title: string; type: string; at: string | null; plant_id?: string | null }>;
  fertilize: Array<{ task_id: string; title: string; type: string; at: string | null; plant_id?: string | null }>;
  repot: Array<{ task_id: string; title: string; type: string; at: string | null; plant_id?: string | null }>;
};

export type DashboardAttention = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  urgency: string;
  next_due_at: string | null;
  recommended_amount: string | null;
  amount_label?: string | null;
  amount_ml?: number | null;
  amount_howto?: string | null;
  best_time_label?: string | null;
  best_time_local?: string | null;
  schedule_plain?: string | null;
  weather_note?: string | null;
  interval_days?: number | null;
  heat_stress?: boolean;
  dry_air?: boolean;
};

export type DiscoverContent = {
  tip_of_day: string;
  weather_nudge?: string | null;
  plant_of_day: {
    name: string;
    common: string;
    why: string;
    emoji: string;
  };
  season_label: string;
  season_intro: string;
  recommendations: Array<{ name: string; tip: string; emoji: string }>;
};

export type Dashboard = {
  tasks_today: CareTask[];
  attention: DashboardAttention[];
  upcoming: CareTask[];
  recent_events: CareEvent[];
  counts: {
    plants_active: number;
    overdue_water: number;
    open_tasks: number;
    due_soon: number;
  };
  weather?: {
    configured: boolean;
    temperature_c?: number | null;
    humidity?: number | null;
    precip_next_24h_mm?: number | null;
    message?: string;
    daily?: DailyWeather[];
  } | null;
  care_brief?: CareBrief | null;
  discover?: DiscoverContent | null;
};

export type LayoutContainer = {
  id: string;
  name: string;
  kind: string | null;
  emoji?: string | null;
  x: number;
  y: number;
  width?: number | null;
  height?: number | null;
  path_json?: number[][];
};

export type LayoutPlacement = {
  id: string;
  plant_id: string;
  container_id: string | null;
  x: number;
  y: number;
  width: number | null;
  height: number | null;
};

export type LayoutSpace = {
  id: string;
  name: string;
  kind: string;
  canvas_width: number;
  canvas_height: number;
  length_m?: number | null;
  width_m?: number | null;
  notes?: string | null;
  sort_order: number;
  containers: LayoutContainer[];
  placements: LayoutPlacement[];
};

export type LayoutSite = {
  id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  sort_order: number;
  spaces: LayoutSpace[];
};

export type StatsSummary = {
  plants_by_status: Record<string, number>;
  plants_active: number;
  plants_deceased: number;
  survival_rate: number | null;
  collection_value: number;
  waterings_30d: number;
  estimated_water_ml_30d: number;
  tasks_completed_30d: number;
  tasks_open: number;
};

export type CalendarItem = {
  id: string;
  kind: string;
  title: string;
  type: string;
  status: string | null;
  at: string | null;
  plant_id?: string | null;
  room?: string | null;
  recommended_amount?: string | null;
  source?: string | null;
  description?: string | null;
};

export type CatalogTaxon = Taxon & {
  preview_url?: string | null;
  suggested_environment?: string;
};
