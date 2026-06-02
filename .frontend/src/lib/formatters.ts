/**
 * Shared formatting utilities for the Coach Platform.
 * Keeps numeric display clean and consistent across all views.
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

/** Round weight to nearest 0.5kg (Hevy stores exact lbs→kg conversions with float noise) */
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

/** Format ISO date to "May 28, 2026" */
export function formatDate(d: string): string {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** Format ISO date to short "May 28" */
export function formatDateShort(d: string): string {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Format sync time as relative: "Just now", "3h ago", "2d ago" */
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
    return `From ${source} ${formatDateShort(timeWindowStart)} – ${formatDateShort(timeWindowEnd)}`;
  }
  if (timeWindowStart) {
    return `From ${source} ${formatDateShort(timeWindowStart)}`;
  }
  return `From ${source}`;
}

/** Get phase style colors */
export function getPhaseStyle(phase: string): { bg: string; text: string } {
  switch (phase) {
    case "blast": return { bg: "rgba(196, 69, 54, 0.1)", text: "#C44536" };
    case "cruise": return { bg: "rgba(74, 127, 165, 0.1)", text: "#4A7FA5" };
    case "prep": return { bg: "rgba(123, 104, 174, 0.1)", text: "#7B68AE" };
    case "offseason": return { bg: "rgba(90, 138, 92, 0.1)", text: "#5A8A5C" };
    case "off": return { bg: "rgba(155, 148, 141, 0.1)", text: "#9B948D" };
    default: return { bg: "rgba(155, 148, 141, 0.1)", text: "#9B948D" };
  }
}

/** Severity color */
export function getSeverityColor(severity: "concerning" | "notable" | "info"): string {
  switch (severity) {
    case "concerning": return "#C44536";
    case "notable": return "#C98B2F";
    case "info": return "#4A7FA5";
  }
}

/** Lab flag colors */
export function getFlagColor(flag: "high" | "low" | "normal"): { bg: string; text: string } {
  switch (flag) {
    case "high": return { bg: "var(--color-severity-concerning-bg)", text: "var(--color-severity-concerning)" };
    case "low": return { bg: "var(--color-severity-notable-bg)", text: "var(--color-severity-notable)" };
    case "normal": return { bg: "var(--color-success-bg)", text: "var(--color-success)" };
  }
}

/** Wearable metric display metadata */
export const WEARABLE_META: Record<string, { label: string; color: string; priority: number }> = {
  weight_kg: { label: "Weight", color: "#C98B2F", priority: 1 },
  weight: { label: "Weight", color: "#C98B2F", priority: 1 },
  resting_hr: { label: "Resting HR", color: "#C44536", priority: 2 },
  hrv_rmssd: { label: "HRV (RMSSD)", color: "#4A7FA5", priority: 3 },
  hrv_sdnn: { label: "HRV (SDNN)", color: "#4A7FA5", priority: 3 },
  hrv: { label: "HRV", color: "#4A7FA5", priority: 3 },
  bp_systolic: { label: "BP (Systolic)", color: "#C44536", priority: 4 },
  bp_diastolic: { label: "BP (Diastolic)", color: "#C98B2F", priority: 4 },
  recovery_score: { label: "Recovery", color: "#5A8A5C", priority: 10 },
  recovery: { label: "Recovery", color: "#5A8A5C", priority: 10 },
  heart_rate: { label: "Heart Rate", color: "#C44536", priority: 5 },
};

/** Signal label → wearable metric key mapping for finding graphs */
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
