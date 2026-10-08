/**
 * Hand-maintained types for the AI Lab run (POST /api/lab/run, SSE) — kept
 * against storelab/agent.py directly, the same reasoning as LabEvent in
 * client.ts. `LabDone` extends the server's raw "done" event with the
 * fields the frontend accumulates client-side while streaming (steps,
 * diagnosis, overrides) — exactly what the old app's onEvent() did.
 */

export interface ObjectiveSpec {
  raw_text: string;
  language: string;
  normalized_objective: string;
  metric: 'category_revenue' | 'category_units' | 'category_attachment' | 'total_revenue' | 'basket_value';
  target_category: string | null;
  target_uplift_pct: number | null;
  budget_php: number;
  budget_stated: boolean;
  max_congestion_increase_pct: number;
  congestion_stated: boolean;
  fixed_categories: string[];
  notes: string[];
  source: 'gemini' | 'offline';
}

export interface ObjectiveOverrides {
  budget_php?: number;
  max_congestion_increase_pct?: number;
  target_uplift_pct?: number;
  target_category?: 'bakery' | 'coffee' | 'snacks' | 'beverages';
}

export interface ChangeDelta {
  label: string;
  relative_pct: number;
  ci_low_pct: number;
  ci_high_pct: number;
}

export interface SimulationResult {
  deltas: { primary: ChangeDelta; congestion: ChangeDelta };
  kpis: unknown;
  congestion: unknown;
  category: unknown;
  heatmap: number[][];
  journeys: number;
  seconds: number;
}

export interface Gate {
  passed: boolean;
  at_risk: boolean;
  reason: string;
}

export interface Candidate {
  id: string;
  round: number;
  source: 'gemini' | 'offline';
  name: string;
  hypothesis: string;
  rationale: string;
  expected_mechanism: string;
  changes: unknown[];
  descriptions: string[];
  cost: number;
  valid: boolean | null;
  errors: string[];
  warnings: string[];
  simulation: SimulationResult | null;
  gate: Gate | null;
  verdict: 'keep' | 'reject' | null;
  verdict_reason: string | null;
  verdict_source: string | null;
  status: 'proposed' | 'simulated' | 'kept' | 'rejected' | 'recommended';
  layout?: { category_slot: Record<string, string>; displays: Record<string, string> };
}

export interface RecommendationExplanation {
  title: string;
  why: string;
  expected_summary: string;
  risks: string[];
}

export interface Recommendation {
  candidate_id: string;
  explanation: RecommendationExplanation;
  explanation_source: 'gemini' | 'offline';
  meets_target: boolean | null;
  target_pct: number | null;
}

export interface DiagnosisInsight {
  observation: string;
  hypothesis: string;
}

export interface StepLogEntry {
  title: string;
  source: string;
  detail: string;
  fallback: string | null;
}

export interface ToolCallEntry {
  name: string;
  args: string;
  summary: string;
}

export interface AgentPublicSettings {
  mode: 'gemini-api' | 'vertex-ai' | 'offline';
  model?: string;
  reason?: string;
}

/** The server's raw "done" event (agent.py LabAgent.run(), the final yield). */
export interface LabDoneRaw {
  run_id: string;
  objective: ObjectiveSpec;
  candidates: Candidate[];
  ranking: unknown;
  recommendation: Recommendation | null;
  plan: unknown;
  agent: AgentPublicSettings;
  gemini_calls: number;
  fallbacks: string[];
  tool_calls: ToolCallEntry[];
  seconds: number;
}

/** What the frontend keeps once a run finishes — the raw event plus what it accumulated while streaming. */
export interface LabDone extends LabDoneRaw {
  steps: StepLogEntry[];
  diagnosis: DiagnosisInsight[];
  overrides: ObjectiveOverrides | null;
}

/** storelab/pilot.py plan_pilot() — a real-store test-vs-control plan for one simulated candidate. */
export interface PilotStoreRow {
  store_id: string;
  name: string;
  format: string;
  weekly_visitors: number;
}

export interface PilotPlan {
  title: string;
  experiment_id: string;
  changes: string[];
  cost_per_store_php: number;
  total_install_cost_php: number;
  test_stores: PilotStoreRow[];
  control_stores: PilotStoreRow[];
  pre_period_days: number;
  duration_days: number;
  primary_kpi: string;
  success_criterion: string;
  guardrails: string[];
  expected: {
    primary_pct: number;
    primary_ci_pct: [number, number];
    congestion_pct: number;
    congestion_ci_pct: [number, number];
    revenue_pct: number;
  };
  power: {
    alpha: number;
    power: number;
    daily_kpi_cv: number;
    stores_per_arm: number;
    days_needed_exact: number | null;
    minimum_detectable_effect_pct: number;
    underpowered: boolean;
    method: string;
    note?: string;
  };
  schedule: string[];
  status: string;
}

/** storelab/main.py create_pilot() — the record returned once a plan is actually launched. */
export interface PilotRecord {
  pilot_id: string;
  status: string;
  created_at: string;
  objective: string | null;
  plan: PilotPlan;
  note: string;
}
