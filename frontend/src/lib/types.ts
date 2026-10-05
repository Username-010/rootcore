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

export type WeekRoundPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  urgency: string;
  next_due_at: string | null;
  recommended_amount: string | null;
  amount_label?: string | null;
  best_time_label?: string | null;
};

export type WeekRoundTask = {
  id: string;
  title: string;
  type: string;
  due_at: string | null;
};

export type WeekRoundDay = {
  date: string;
  weekday: string;
  is_today: boolean;
  plants: WeekRoundPlant[];
  tasks: WeekRoundTask[];
};

export type WeekRound = {
  timezone: string;
  generated_at: string;
  from: string;
  to: string;
  days: WeekRoundDay[];
  counts: { plants: number; tasks: number };
};


export type GardenWatchAlert = {
  kind: string;
  severity: string;
  date: string;
  title: string;
  detail: string;
};

export type GardenWatchNight = {
  date: string;
  weekday: string;
  is_today: boolean;
  temp_min_c: number | null;
  temp_max_c: number | null;
  precip_mm: number | null;
  weather_code: number | null;
  frost_hard: boolean;
  frost_risk: boolean;
  rain_skip: boolean;
  heat: boolean;
  flags: string[];
};

export type GardenWatchPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  space_name: string;
  space_kind: string;
};

export type DueCanPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  urgency: string;
  next_due_at: string | null;
  recommended_amount: string | null;
};

export type DueCan = {
  timezone: string;
  generated_at: string;
  summary: string;
  groups: {
    overdue: DueCanPlant[];
    due: DueCanPlant[];
    soon: DueCanPlant[];
  };
  counts: { overdue: number; due: number; soon: number };
  total: number;
};

export type GardenWatch = {
  timezone: string;
  generated_at: string;
  configured: boolean;
  summary: string;
  alerts: GardenWatchAlert[];
  nights: GardenWatchNight[];
  outdoor_plants: GardenWatchPlant[];
  counts: {
    frost_nights: number;
    rain_days: number;
    outdoor_plants: number;
    alerts: number;
  };
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

export type LabelSheetCard = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  common_name?: string | null;
};

export type LabelSheet = {
  timezone: string;
  generated_at: string;
  summary: string;
  cards: LabelSheetCard[];
  total: number;
};

export type AwaySheetPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  notes?: string | null;
  pot_size_liters?: number | null;
  soil_type?: string | null;
};

export type AwaySheet = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: AwaySheetPlant[];
  total: number;
};

export type NurseryRunPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  pot_size_liters?: number | null;
  soil_type?: string | null;
  need_soil: boolean;
  need_pot: boolean;
  need_feed: boolean;
};

export type NurseryRunSoil = {
  soil_type: string;
  plants: number;
  bags: number;
};

export type NurseryRun = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: NurseryRunPlant[];
  soils: NurseryRunSoil[];
  total: number;
  soil_kinds: number;
};

export type CuttingsTrayPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  method: string;
  method_label: string;
  already_child: boolean;
};

export type CuttingsTray = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: CuttingsTrayPlant[];
  total: number;
  water_jars: number;
  soil_pots: number;
};

export type RepotBenchPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  pot_size_liters?: number | null;
  pot_material?: string | null;
  next_pot_liters?: number | null;
  next_label: string;
  needs_measure: boolean;
};

export type RepotBench = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: RepotBenchPlant[];
  total: number;
  sized: number;
  needs_measure: number;
};

export type FeedMixPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  strength: string;
  mix_label: string;
  skip: boolean;
};

export type FeedMix = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: FeedMixPlant[];
  total: number;
  half: number;
  full: number;
  skip: number;
};

export type PruneListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  cut: string;
  cut_label: string;
  skip: boolean;
};

export type PruneList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: PruneListPlant[];
  total: number;
  hard: number;
  pinch: number;
  light: number;
  skip: number;
};

export type MistListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  mist: string;
  mist_label: string;
  skip: boolean;
};

export type MistList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: MistListPlant[];
  total: number;
  fine: number;
  light: number;
  pebble: number;
  skip: number;
};

export type DustListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  dust: string;
  dust_label: string;
  skip: boolean;
};

export type DustList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: DustListPlant[];
  total: number;
  cloth: number;
  damp: number;
  rinse: number;
  skip: number;
};

export type RotateListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  rotate: string;
  rotate_label: string;
  skip: boolean;
};

export type RotateList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: RotateListPlant[];
  total: number;
  quarter: number;
  half: number;
  skip: number;
};

export type PestWalkPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  pest: string;
  pest_label: string;
  skip: boolean;
};

export type PestWalk = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: PestWalkPlant[];
  total: number;
  look: number;
  sticky: number;
  isolate: number;
  skip: number;
};

export type StakeListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  stake: string;
  stake_label: string;
  skip: boolean;
};

export type StakeList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: StakeListPlant[];
  total: number;
  moss: number;
  cane: number;
  check: number;
  skip: number;
};

export type HarvestListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  harvest: string;
  harvest_label: string;
  skip: boolean;
};

export type HarvestList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: HarvestListPlant[];
  total: number;
  leaf: number;
  fruit: number;
  look: number;
  skip: number;
};

export type LightMapPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  light: string;
  light_label: string;
  skip: boolean;
};

export type LightMap = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: LightMapPlant[];
  total: number;
  shade: number;
  bright: number;
  direct: number;
  skip: number;
};

export type FrostListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  frost: string;
  frost_label: string;
  skip: boolean;
};

export type FrostList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: FrostListPlant[];
  total: number;
  bring: number;
  cover: number;
  dry: number;
  skip: number;
};

export type GroomListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  groom: string;
  groom_label: string;
  skip: boolean;
};

export type GroomList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: GroomListPlant[];
  total: number;
  yellow: number;
  bloom: number;
  skip: number;
};

export type FlushListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  flush: string;
  flush_label: string;
  skip: boolean;
};

export type FlushList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: FlushListPlant[];
  total: number;
  soak: number;
  drain: number;
  dump: number;
  skip: number;
};

export type SplitListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  split: string;
  split_label: string;
  skip: boolean;
};

export type SplitList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: SplitListPlant[];
  total: number;
  look: number;
  divide: number;
  pot: number;
  skip: number;
};

export type SowListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  sow: string;
  sow_label: string;
  skip: boolean;
};

export type SowList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: SowListPlant[];
  total: number;
  look: number;
  sow: number;
  cover: number;
  skip: number;
};

export type HardenListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  harden: string;
  harden_label: string;
  skip: boolean;
};

export type HardenList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: HardenListPlant[];
  total: number;
  look: number;
  shade: number;
  wind: number;
  skip: number;
};

export type MulchListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  mulch: string;
  mulch_label: string;
  skip: boolean;
};

export type MulchList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: MulchListPlant[];
  total: number;
  look: number;
  crown: number;
  mulch: number;
  skip: number;
};

export type TopdressListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  topdress: string;
  topdress_label: string;
  skip: boolean;
};

export type TopdressList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: TopdressListPlant[];
  total: number;
  look: number;
  thin: number;
  topdress: number;
  skip: number;
};

export type BottomListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  bottom: string;
  bottom_label: string;
  skip: boolean;
};

export type BottomList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: BottomListPlant[];
  total: number;
  look: number;
  soak: number;
  drain: number;
  skip: number;
};

export type AirListPlant = {
  plant_id: string;
  nickname: string;
  emoji?: string | null;
  environment: string;
  scientific_name?: string | null;
  air: string;
  air_label: string;
  skip: boolean;
};

export type AirList = {
  timezone: string;
  generated_at: string;
  household_name: string;
  summary: string;
  plants: AirListPlant[];
  total: number;
  look: number;
  draft: number;
  fan: number;
  skip: number;
};
