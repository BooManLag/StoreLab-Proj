/**
 * Hand-maintained response types for the endpoints that return a bare FastAPI
 * `Response` instead of a Pydantic model (storelab/main.py: store_geometry,
 * analytics, journey_sample all declare `-> Response` and build JSON by
 * hand). The OpenAPI schema can't describe those bodies — `schema.d.ts`
 * types them as `unknown` — so these are kept against main.py directly, the
 * same reasoning as `LabEvent` in client.ts. Only fields the frontend
 * actually reads are typed precisely; the rest (`products`, `network`,
 * `hourly`, `clusters`, `transitions`, `insights`, `sequence_effects`, etc.)
 * stay `unknown` until the screen that needs them is built.
 */

export interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface Fixture extends Rect {
  id: string;
  label: string;
  kind: string;
  refrigerated: boolean;
}

export interface Aisle extends Rect {
  id: string;
  label: string;
  refrigerated: boolean;
  anchor: string;
}

export interface DisplaySlot extends Rect {
  id: string;
  label: string;
  kind: string;
  add_cost: number;
  free_standing: boolean;
  clear_width_m: number;
  restricted: boolean;
  restricted_reason: string | null;
  at_checkout: boolean;
}

export interface Layout {
  category_slot: Record<string, string>;
  displays: Record<string, string>;
}

export interface StoreGeometry {
  id: string;
  name: string;
  region: string;
  currency: string;
  timezone: string;
  width: number;
  height: number;
  cell_m: number;
  fixtures: Fixture[];
  aisles: Aisle[];
  displays: DisplaySlot[];
  areas: {
    entrance: Rect;
    checkout: Rect;
    exit: Rect;
    entrance_door: Rect;
    exit_door: Rect;
  };
  categories: { id: string; label: string }[];
  baseline_layout: Layout;
  products: unknown[];
  network: unknown[];
  costs: { move_display: number; remove_display: number; swap_categories: number };
  constraints: { min_aisle_width_m: number; max_changes: number; refrigerated_fixed: boolean; peak_window: [number, number] };
}

export interface BriefingAction {
  type: 'goal' | 'analytics';
  label: string;
  goal?: string;
  target?: string;
}

export interface BriefingItem {
  kind: 'opportunity' | 'friction' | 'pattern';
  title: string;
  detail: string;
  zones: string[];
  action: BriefingAction;
}

export interface ZoneStat {
  label: string;
  category: string;
  visitors: number;
  engaged: number;
  purchases: number;
  zone_conversion: number;
  traffic_share: number;
  attachment_rate: number;
  category_buyers: number;
  revenue: number;
  avg_dwell_s: number;
}

export interface AnalyticsSummary {
  kpis: {
    visitors: number;
    transactions: number;
    conversion_rate: number;
    avg_basket: number;
    items_per_basket: number;
    peak_checkout_occupancy: number;
    peak_window: string;
    days: number;
    period: string;
  };
  briefing: BriefingItem[];
  zones: Record<string, ZoneStat>;
  sequence_effects: { from: string; to: string; ratio: number; conversion_after_from: number }[];
  hourly: { hour: number; checkout_occupancy: number; transactions_per_day: number }[];
  clusters: { name: string; share: number; conversion: number; top_paths: { path: string }[] }[];
  transitions: { labels: string[]; probabilities: number[][] };
  insights: { title: string; detail: string }[];
  pos_join: { transactions: number; matched: number; match_rate: number; window_s: number; method: string; accuracy_vs_synthetic_truth: number };
}

export interface AnalyticsModel {
  segments: unknown;
  journeys: unknown;
  transition_model: {
    n_choices: number; log_likelihood: number; converged: boolean;
    beta_dist_per_m: number; beta_complement: number; beta_revisit: number; beta_done_per_zone: number;
  };
  purchase_model: unknown;
  display_engagement: unknown;
  checkout_model: {
    n_idle_counter_customers: number; base_s: number; per_item_s: number; sd_s: number;
    lanes: number; rack_dwell_s: number; rack_dwell_source: string;
  };
  /** Category pairs bought together more than chance, e.g. [["bakery","coffee"]]. */
  complements: string[][];
}

export interface AnalyticsCalibration {
  rows: { metric: string; observed: number; simulated: number; error_pct: number }[];
  max_abs_error_pct: number;
  note: string;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  heatmap: number[][];
  heatmap_units: string;
  model: AnalyticsModel;
  calibration: AnalyticsCalibration;
}

export interface JourneyTrack {
  /** String for real anonymized history (/api/journeys/sample, e.g. "anon_068157"); a plain number for freshly-simulated tracks (/api/tracks). */
  id: string | number;
  bought: boolean;
  /** [seconds-from-window-start, x-meters, y-meters][] */
  points: [number, number, number][];
}

export interface ConfigResponse {
  version: string;
  agent: { mode: 'gemini-api' | 'vertex-ai' | 'offline'; model?: string; reason?: string };
  synthetic_data: boolean;
  store: { id: string; name: string; region: string; currency: string };
  history: { journeys: number; transactions: number; days: number; period: string };
  simulator: { journeys_per_run: number; days_per_run: number };
  built_at: string;
}

export interface JourneySample {
  day: number;
  start: number;
  window_s: number;
  tracks: JourneyTrack[];
}

/** POST /api/tracks — animated virtual shoppers for a given layout; same synthetic shoppers for every layout. */
export interface TracksResponse {
  start: number;
  window_s: number;
  tracks: JourneyTrack[];
}
