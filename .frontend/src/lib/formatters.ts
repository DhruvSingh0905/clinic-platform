/**
 * Shared formatting utilities for the Clinic Platform.
 */

/** Get unit preference (stored in localStorage) */
export function getUnitPref(): "kg" | "lbs" {
  if (typeof window === "undefined") return "kg";
  return (localStorage.getItem("unit_pref") as "kg" | "lbs") || "kg";
}

export function setUnitPref(unit: "kg" | "lbs") {
  if (typeof window !== "undefined") localStorage.setItem("unit_pref", unit);
}

function kgToLbs(kg: number): number { return kg * 2.20462; }

/** Round weight to nearest 0.5kg */
export function cleanWeight(kg: number): number {
  return Math.round(kg * 2) / 2;
}

/** Format a weight for display — respects unit preference */
export function formatWeight(kg: number): string {
  const pref = getUnitPref();
  if (pref === "lbs") {
    const lbs = Math.round(kgToLbs(kg));
    return `${lbs}lbs`;
  }
  const clean = cleanWeight(kg);
  return clean % 1 === 0 ? `${clean}kg` : `${clean.toFixed(1)}kg`;
}

/** Format a metric value based on its type */
export function formatMetric(value: number, unit: string): string {
  if (unit === "kg" || unit === "lbs") return formatWeight(value);
  if (unit === "bpm" || unit === "%" || unit === "ms") return `${Math.round(value)} ${unit}`;
  if (unit === "mg/dL" || unit === "U/L" || unit === "mEq/L" || unit === "M/uL") {
    return value % 1 === 0 ? `${value} ${unit}` : `${value.toFixed(1)} ${unit}`;
  }
  return `${Math.round(value * 10) / 10} ${unit}`;
}

/** Ensure date-only strings are treated as local time, not UTC */
function localDate(d: string): Date {
  // "2026-07-02" → parsed as UTC by Date constructor → off-by-one in negative timezones
  // Adding T12:00:00 ensures it stays on the correct day in any timezone
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return new Date(d + "T12:00:00");
  return new Date(d);
}

/** Format ISO date to "May 28, 2026" */
export function formatDate(d: string): string {
  return localDate(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** Format ISO date to short "May 28" */
export function formatDateShort(d: string): string {
  return localDate(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Format sync time as relative */
export function formatSyncTime(sync: string | null): string {
  if (!sync) return "Never synced";
  const d = new Date(sync);
  const now = new Date();
  const diffH = Math.floor((now.getTime() - d.getTime()) / 3600000);
  if (diffH < 1) return "Just now";
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

/** Derive finding provenance from theme + time window */
export function findingProvenance(theme: string, timeWindowStart?: string, timeWindowEnd?: string): string {
  const sourceMap: Record<string, string> = {
    hematological: "bloodwork",
    hepatic: "bloodwork",
    cardiovascular: "wearable data",
    metabolic: "wearable data",
    hormonal: "bloodwork",
    renal: "bloodwork",
    inflammation: "bloodwork",
    recovery: "wearable data",
    training: "workout data",
  };
  const source = sourceMap[theme] || "data";
  if (timeWindowStart && timeWindowEnd) {
    return `${source} · ${formatDateShort(timeWindowStart)} – ${formatDateShort(timeWindowEnd)}`;
  }
  if (timeWindowStart) {
    return `${source} · ${formatDateShort(timeWindowStart)}`;
  }
  return source;
}

/** Treatment status style — muted, functional */
export function getStatusStyle(status: string): { bg: string; text: string } {
  switch (status) {
    case "active_treatment": return { bg: "rgba(63, 185, 80, 0.1)", text: "#3FB950" };
    case "monitoring": return { bg: "rgba(76, 141, 255, 0.1)", text: "#4C8DFF" };
    case "tapering": return { bg: "rgba(212, 149, 42, 0.1)", text: "#D4952A" };
    case "discontinued": return { bg: "rgba(86, 91, 110, 0.1)", text: "#565B6E" };
    case "initial_consult": return { bg: "rgba(163, 113, 247, 0.1)", text: "#A371F7" };
    default: return { bg: "rgba(86, 91, 110, 0.1)", text: "#565B6E" };
  }
}

/** Severity color */
export function getSeverityColor(severity: "concerning" | "notable" | "info"): string {
  switch (severity) {
    case "concerning": return "#E5534B";
    case "notable": return "#D4952A";
    case "info": return "#4C8DFF";
  }
}

/** Lab flag colors */
export function getFlagColor(flag: string | null | undefined): { bg: string; text: string } {
  switch (flag) {
    case "high": return { bg: "var(--color-severity-concerning-bg)", text: "var(--color-severity-concerning)" };
    case "low": return { bg: "var(--color-severity-notable-bg)", text: "var(--color-severity-notable)" };
    case "normal": return { bg: "var(--color-success-bg)", text: "var(--color-success)" };
    default: return { bg: "rgba(86, 91, 110, 0.1)", text: "var(--color-text-muted)" };
  }
}

/** Wearable metric display metadata */
export const WEARABLE_META: Record<string, { label: string; color: string; priority: number }> = {
  weight_kg: { label: "Weight", color: "#D4952A", priority: 1 },
  weight: { label: "Weight", color: "#D4952A", priority: 1 },
  resting_hr: { label: "Resting HR", color: "#E5534B", priority: 2 },
  hrv_rmssd: { label: "HRV (RMSSD)", color: "#4C8DFF", priority: 3 },
  hrv_sdnn: { label: "HRV (SDNN)", color: "#4C8DFF", priority: 3 },
  hrv: { label: "HRV", color: "#4C8DFF", priority: 3 },
  bp_systolic: { label: "BP Sys", color: "#E5534B", priority: 4 },
  bp_diastolic: { label: "BP Dia", color: "#D4952A", priority: 4 },
  recovery_score: { label: "Recovery", color: "#3FB950", priority: 10 },
  recovery: { label: "Recovery", color: "#3FB950", priority: 10 },
  calories_consumed: { label: "Calories", color: "#D4952A", priority: 11 },
  protein: { label: "Protein", color: "#E5534B", priority: 12 },
  fat: { label: "Fat", color: "#4C8DFF", priority: 13 },
  carbs: { label: "Carbs", color: "#D4952A", priority: 14 },
  training_duration: { label: "Training Duration", color: "#A371F7", priority: 15 },
  training_calories: { label: "Training Calories", color: "#A371F7", priority: 16 },
  training_load: { label: "Training Load", color: "#A371F7", priority: 17 },
  heart_rate: { label: "Heart Rate", color: "#E5534B", priority: 5 },
};

/** Signal label -> wearable metric key mapping for finding graphs */
export const SIGNAL_TO_METRIC: Record<string, string> = {
  "Resting HR": "resting_hr",
  "Resting Heart Rate": "resting_hr",
  "HR": "resting_hr",
  "HRV": "hrv_rmssd",
  "HRV (RMSSD)": "hrv_rmssd",
  "Recovery": "recovery_score",
  "Weight": "weight_kg",
  "Hematocrit": "2930-0",
  "RBC": "789-8",
  "ALT": "1742-6",
  "AST": "1920-8",
  "HDL": "2085-9",
  "LDL": "2571-8",
  "Total Chol": "2093-3",
  "Total Cholesterol": "2093-3",
  "Triglycerides": "2571-8",
  "Fasting Glucose": "2345-7",
  "Glucose CV": "",
};
