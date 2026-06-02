export interface Coach {
  id: string;
  name: string;
  email: string;
}

export interface Athlete {
  id: string;
  name: string;
  email: string;
  avatar_color: string;
  connected_at: string;
  last_sync: string | null;
  integrations: string[];
}

export interface Signal {
  label: string;
  value: string;
  direction?: "up" | "down" | "flat";
  delta?: string;
}

export interface Finding {
  id: string;
  athlete_id?: string;
  athlete_name?: string;
  detector_id: string;
  theme: string;
  severity: "concerning" | "notable" | "info";
  headline: string;
  summary: string;
  signals: Signal[];
  detected_at: string;
  status: "active" | "viewed" | "resolved" | "dismissed";
  time_window_start?: string;
  time_window_end?: string;
}

export interface RosterEntry {
  athlete: Athlete;
  top_finding: Finding | null;
  finding_count: number;
  phase: string;
  day_in_phase: number;
}

export interface SubstanceEvent {
  compound_name: string;
  compound_class: string;
  event_type: "START" | "DOSE_CHANGE" | "STOP" | "MISSED_DOSE";
  dose_mg: number | null;
  frequency: string | null;
  route: string | null;
  timestamp: string;
}

export interface DrugLevel {
  compound_name: string;
  compound_class: string;
  level: number;
  dose_active_mg: number;
  at_steady_state: boolean;
  observation_date: string;
}

export interface WearableMetric {
  metric: string;
  observation_date: string;
  value_mean: number;
  unit: string;
  source: string;
  methodology?: string;
}

export interface LabResult {
  metric_loinc: string;
  metric_name: string;
  value_canonical: number;
  unit_canonical: string;
  observation_date: string;
  flag: "high" | "low" | "normal";
  reference_low: number;
  reference_high: number;
  category: string;
}

export interface TrainingBlock {
  id: string;
  name: string;
  block_type: string;
  start_date: string;
  end_date: string | null;
  notes: string | null;
  status: "active" | "completed" | "planned";
}

export interface NutritionTarget {
  id: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  notes: string | null;
  effective_date: string;
}

export interface RecoveryNote {
  id: string;
  note_type: string;
  content: string;
  created_at: string;
}

export interface ClientDetail {
  athlete: Athlete;
  phase: string;
  phase_started_at?: string;
  day_in_phase: number;
  findings: Finding[];
  wearables: WearableMetric[];
  labs: LabResult[];
  substance_events: SubstanceEvent[];
  drug_levels: DrugLevel[];
  training: TrainingBlock[];
  nutrition: NutritionTarget[];
  recovery: RecoveryNote[];
}

export interface LiftSession {
  date: string;
  working_weight_kg: number;
  best_set_reps: number;
  estimated_1rm: number;
  total_volume_kg: number;
  set_count: number;
}

export interface LiftData {
  exercise_name: string;
  exercise_template_id: string;
  sessions: LiftSession[];
  status: "stall" | "drop" | "progressing";
  trend_pct: number;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  detail_json: string | null;
  read: number;
  created_at: string;
}
