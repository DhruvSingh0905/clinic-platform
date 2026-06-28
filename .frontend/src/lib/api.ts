import type { RosterEntry, PatientDetail, LiftData, RoutinePush } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Clinician endpoints
export async function getRoster(clinicianId: string): Promise<RosterEntry[]> {
  const data = await fetchJSON<{ roster: RosterEntry[] }>(`/api/clinician/${clinicianId}/roster`);
  return data.roster;
}

export async function getPatientDetail(clinicianId: string, patientId: string): Promise<PatientDetail> {
  return fetchJSON<PatientDetail>(`/api/clinician/${clinicianId}/patient/${patientId}`);
}

export async function setTrainingBlock(clinicianId: string, patientId: string, block: {
  name: string; start_date: string; end_date?: string; notes?: string;
}) {
  return fetchJSON(`/api/clinician/${clinicianId}/patient/${patientId}/training`, {
    method: "POST",
    body: JSON.stringify(block),
  });
}

export async function setNutritionTarget(clinicianId: string, patientId: string, target: {
  calories: number; protein_g: number; carbs_g: number; fat_g: number; effective_date: string; notes?: string;
}): Promise<void> {
  await fetchJSON(`/api/clinician/${clinicianId}/patient/${patientId}/nutrition`, {
    method: "POST",
    body: JSON.stringify(target),
  });
}

export async function addRecoveryNote(clinicianId: string, patientId: string, note: {
  note_type: string; content: string;
}) {
  return fetchJSON(`/api/clinician/${clinicianId}/patient/${patientId}/recovery`, {
    method: "POST",
    body: JSON.stringify(note),
  });
}

// Patient endpoints
export async function getPatientDashboard(patientId: string): Promise<Record<string, unknown>> {
  return fetchJSON<Record<string, unknown>>(`/api/patient/${patientId}/dashboard`);
}

export async function logSubstanceEvent(patientId: string, event: {
  compound_name: string; compound_class: string; event_type: string;
  dose_mg?: number; frequency?: string; route?: string;
}) {
  return fetchJSON(`/api/patient/${patientId}/substance`, {
    method: "POST",
    body: JSON.stringify(event),
  });
}

// Lift data
export async function getPatientLifts(clinicianId: string, patientId: string, days = 28): Promise<{ lifts: LiftData[]; flagged: string[] }> {
  return fetchJSON<{ lifts: LiftData[]; flagged: string[] }>(`/api/clinician/${clinicianId}/patient/${patientId}/lifts?days=${days}`);
}

// Routines
export async function getPatientRoutines(clinicianId: string, patientId: string): Promise<RoutinePush[]> {
  const data = await fetchJSON<{ routines: RoutinePush[] }>(`/api/clinician/${clinicianId}/patient/${patientId}/routines`);
  return data.routines;
}

// Chat endpoints
export async function sendClinicianChat(clinicianId: string, patientId: string, message: string): Promise<string> {
  const data = await fetchJSON<{ response: string }>(`/api/clinician/${clinicianId}/patient/${patientId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  return data.response;
}

export async function sendPatientChat(patientId: string, message: string): Promise<string> {
  const data = await fetchJSON<{ response: string }>(`/api/patient/${patientId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  return data.response;
}
