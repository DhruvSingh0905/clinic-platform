export interface Clinician {
  id: string;
  name: string;
  email: string;
}

export interface Patient {
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
  patient_id?: string;
  patient_name?: string;
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
  patient: Patient;
  treatment_status: string;
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

export interface PatientDetail {
  patient: Patient;
  treatment_status: string;
  treatment_days?: number;
  treatment_started_at?: string;
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

export interface RoutinePush {
  id: number;
  title: string;
  exercises: { title: string; exercise_template_id: string; sets: { type: string; weight_kg?: number; reps: number }[] }[];
  pushed_at: string;
  status: string;
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
