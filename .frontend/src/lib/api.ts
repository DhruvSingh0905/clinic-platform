import type { RosterEntry, ClientDetail, LiftData } from "./types";

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

// Coach endpoints
export async function getRoster(coachId: string): Promise<RosterEntry[]> {
  const data = await fetchJSON<{ roster: RosterEntry[] }>(`/api/coach/${coachId}/roster`);
  return data.roster;
}

export async function getClientDetail(coachId: string, athleteId: string): Promise<ClientDetail> {
  return fetchJSON<ClientDetail>(`/api/coach/${coachId}/client/${athleteId}`);
}

export async function setTrainingBlock(coachId: string, athleteId: string, block: {
  name: string; block_type: string; start_date: string; end_date?: string; notes?: string;
}) {
  return fetchJSON(`/api/coach/${coachId}/client/${athleteId}/training`, {
    method: "POST",
    body: JSON.stringify(block),
  });
}

export async function setNutritionTarget(coachId: string, athleteId: string, target: {
  calories: number; protein_g: number; carbs_g: number; fat_g: number; effective_date: string; notes?: string;
}) {
  return fetchJSON(`/api/coach/${coachId}/client/${athleteId}/nutrition`, {
    method: "POST",
    body: JSON.stringify(target),
  });
}

export async function addRecoveryNote(coachId: string, athleteId: string, note: {
  note_type: string; content: string;
}) {
  return fetchJSON(`/api/coach/${coachId}/client/${athleteId}/recovery`, {
    method: "POST",
    body: JSON.stringify(note),
  });
}

// Athlete endpoints
export async function getAthleteDashboard(athleteId: string) {
  return fetchJSON(`/api/athlete/${athleteId}/dashboard`);
}

export async function logSubstanceEvent(athleteId: string, event: {
  compound_name: string; compound_class: string; event_type: string;
  dose_mg?: number; frequency?: string; route?: string;
}) {
  return fetchJSON(`/api/athlete/${athleteId}/substance`, {
    method: "POST",
    body: JSON.stringify(event),
  });
}

// Lift data
export async function getClientLifts(coachId: string, athleteId: string, days = 28): Promise<{ lifts: LiftData[]; flagged: string[] }> {
  return fetchJSON<{ lifts: LiftData[]; flagged: string[] }>(`/api/coach/${coachId}/client/${athleteId}/lifts?days=${days}`);
}

// Chat endpoints
export async function sendCoachChat(coachId: string, athleteId: string, message: string, findingId?: string): Promise<string> {
  const data = await fetchJSON<{ response: string }>(`/api/coach/${coachId}/client/${athleteId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, thread_type: findingId ? "finding" : "free", finding_id: findingId }),
  });
  return data.response;
}

export async function sendAthleteChat(athleteId: string, message: string, findingId?: string): Promise<string> {
  const data = await fetchJSON<{ response: string }>(`/api/athlete/${athleteId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, thread_type: findingId ? "finding" : "free", finding_id: findingId }),
  });
  return data.response;
}
