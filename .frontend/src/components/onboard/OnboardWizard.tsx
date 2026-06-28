"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface ColumnMapping {
  target: string;
  confidence: number;
  note?: string;
}

interface FileData {
  file_id: number;
  filename: string;
  row_count: number;
  headers: string[];
  sample_rows: string[][];
  detected_data_type: string;
  confidence: number;
  column_mappings: Record<string, ColumnMapping>;
  conflicts: { column: string; issue: string; description: string }[];
}

const STEPS = ["Info", "Upload", "Review", "Confirm", "Done"];

export default function OnboardWizard() {
  const [step, setStep] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [patientName, setPatientName] = useState("");
  const [patientEmail, setPatientEmail] = useState("");
  const [files, setFiles] = useState<FileData[]>([]);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ patient_id: string; results: { file_id: number; imported: number; errors: number; data_type: string }[] } | null>(null);

  const startSession = async () => {
    if (!patientName.trim()) return;
    const res = await fetch(`${API}/api/clinician/clinician-001/onboard/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_name: patientName, patient_email: patientEmail }),
    });
    const data = await res.json();
    setSessionId(data.session_id);
    setStep(1);
  };

  const uploadFile = async (file: File) => {
    if (!sessionId) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/api/clinician/clinician-001/onboard/${sessionId}/upload`, { method: "POST", body: form });
      const data: FileData = await res.json();
      setFiles((prev) => [...prev, data]);
    } catch {
      alert("Failed to upload file");
    }
    setUploading(false);
  };

  const confirmImport = async () => {
    if (!sessionId) return;
    setImporting(true);
    try {
      const res = await fetch(`${API}/api/clinician/clinician-001/onboard/${sessionId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_name: patientName, patient_email: patientEmail || null }),
      });
      const data = await res.json();
      setImportResult(data);
      setStep(4);
    } catch {
      alert("Import failed");
    }
    setImporting(false);
  };

  // Data type badge color
  const dtColor = (dt: string) => {
    switch (dt) {
      case "training": return { bg: "var(--color-success-bg)", text: "var(--color-success)" };
      case "nutrition": return { bg: "var(--color-severity-notable-bg)", text: "var(--color-severity-notable)" };
      case "bloodwork": return { bg: "var(--color-severity-concerning-bg)", text: "var(--color-severity-concerning)" };
      case "protocol": return { bg: "var(--color-severity-concerning-bg)", text: "var(--color-severity-concerning)" };
      case "vitals": return { bg: "var(--color-accent-light)", text: "var(--color-accent-primary)" };
      default: return { bg: "var(--color-bg-hover)", text: "var(--color-text-muted)" };
    }
  };

  return (
    <div>
      {/* Step indicator */}
      <div className="flex items-center gap-1 mb-6">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <div
              className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-medium"
              style={{
                background: i <= step ? "var(--color-accent-primary)" : "var(--color-bg-hover)",
                color: i <= step ? "#fff" : "var(--color-text-muted)",
              }}
            >
              {i < step ? "\u2713" : i + 1}
            </div>
            <span className="text-[10px] mr-2" style={{ color: i === step ? "var(--color-text-primary)" : "var(--color-text-muted)" }}>{s}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-px" style={{ background: i < step ? "var(--color-accent-primary)" : "var(--color-border-light)" }} />}
          </div>
        ))}
      </div>

      {/* Step 0: Basic Info */}
      {step === 0 && (
        <div className="border p-4 space-y-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          <h3 className="text-sm font-semibold">Patient Information</h3>
          <div>
            <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Name *</label>
            <input type="text" value={patientName} onChange={(e) => setPatientName(e.target.value)} placeholder="Full name" className="w-full text-xs px-3 py-2 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
          </div>
          <div>
            <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Email</label>
            <input type="email" value={patientEmail} onChange={(e) => setPatientEmail(e.target.value)} placeholder="Optional" className="w-full text-xs px-3 py-2 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
          </div>
          <button onClick={startSession} disabled={!patientName.trim()} className="text-xs font-medium px-4 py-2 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>Continue</button>
        </div>
      )}

      {/* Step 1: File Upload */}
      {step === 1 && (
        <div className="space-y-3">
          <div className="border p-4" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <h3 className="text-sm font-semibold mb-1">Upload Spreadsheets</h3>
            <p className="text-[10px] mb-3" style={{ color: "var(--color-text-muted)" }}>Upload Excel (.xlsx) or CSV files containing training programs, nutrition plans, bloodwork results, or protocol data. Our AI will analyze and map the columns.</p>
            <label className="block border-2 border-dashed p-6 text-center cursor-pointer hover:opacity-80 transition-opacity" style={{ borderColor: "var(--color-border-emphasis)", borderRadius: "3px" }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" className="mx-auto mb-2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" /></svg>
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{uploading ? "Analyzing..." : "Drop files here or click to browse"}</p>
              <p className="text-[9px] mt-1" style={{ color: "var(--color-text-muted)" }}>.xlsx, .csv</p>
              <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadFile(f); }} disabled={uploading} />
            </label>
          </div>

          {/* Uploaded files list */}
          {files.length > 0 && (
            <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              {files.map((f, i) => {
                const dt = dtColor(f.detected_data_type);
                return (
                  <div key={f.file_id}>
                    {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-light)" }} />}
                    <div className="px-3 py-2.5 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium truncate">{f.filename}</span>
                          <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase" style={{ background: dt.bg, color: dt.text, borderRadius: "2px" }}>{f.detected_data_type}</span>
                        </div>
                        <p className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{f.row_count} rows · {f.headers.length} columns · {Math.round(f.confidence * 100)}% confidence</p>
                      </div>
                      {f.conflicts.length > 0 && (
                        <span className="text-[9px] font-medium px-1.5 py-0.5" style={{ background: "var(--color-severity-notable-bg)", color: "var(--color-severity-notable)", borderRadius: "2px" }}>{f.conflicts.length} conflicts</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => setStep(0)} className="text-xs px-3 py-1.5" style={{ color: "var(--color-text-muted)" }}>Back</button>
            {files.length > 0 && (
              <button onClick={() => setStep(2)} className="text-xs font-medium px-4 py-1.5 text-white" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>Review Mappings</button>
            )}
          </div>
        </div>
      )}

      {/* Step 2: Review Mappings */}
      {step === 2 && (
        <div className="space-y-4">
          {files.map((f) => (
            <div key={f.file_id} className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              <div className="px-3 py-2 border-b" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)" }}>
                <span className="text-xs font-medium">{f.filename}</span>
                <span className="text-[9px] ml-2 px-1.5 py-0.5 uppercase" style={{ background: dtColor(f.detected_data_type).bg, color: dtColor(f.detected_data_type).text, borderRadius: "2px" }}>{f.detected_data_type}</span>
              </div>
              {/* Column mapping table */}
              <div className="text-[10px]">
                <div className="grid grid-cols-12 gap-2 px-3 py-1.5 font-medium uppercase tracking-wider border-b" style={{ color: "var(--color-text-muted)", borderColor: "var(--color-border-light)" }}>
                  <div className="col-span-4">Source Column</div>
                  <div className="col-span-4">Maps To</div>
                  <div className="col-span-2">Confidence</div>
                  <div className="col-span-2">Note</div>
                </div>
                {Object.entries(f.column_mappings).map(([col, mapping]) => {
                  const isSkip = mapping.target === "skip";
                  const isLow = mapping.confidence < 0.7;
                  return (
                    <div key={col} className="grid grid-cols-12 gap-2 px-3 py-1.5 border-b items-center" style={{ borderColor: "var(--color-border-light)", background: isLow ? "var(--color-severity-notable-bg)" : "transparent" }}>
                      <span className="col-span-4 font-medium" style={{ color: "var(--color-text-primary)" }}>{col}</span>
                      <span className="col-span-4" style={{ fontFamily: "'IBM Plex Mono', monospace", color: isSkip ? "var(--color-text-muted)" : "var(--color-accent-primary)" }}>{mapping.target}</span>
                      <span className="col-span-2" style={{ fontFamily: "'IBM Plex Mono', monospace", color: isLow ? "var(--color-severity-notable)" : "var(--color-text-muted)" }}>{Math.round(mapping.confidence * 100)}%</span>
                      <span className="col-span-2 truncate" style={{ color: "var(--color-text-muted)" }}>{mapping.note || ""}</span>
                    </div>
                  );
                })}
              </div>
              {/* Conflicts */}
              {f.conflicts.length > 0 && (
                <div className="px-3 py-2 border-t" style={{ borderColor: "var(--color-border-light)", background: "var(--color-severity-notable-bg)" }}>
                  <p className="text-[9px] font-medium uppercase tracking-wider mb-1" style={{ color: "var(--color-severity-notable)" }}>Conflicts</p>
                  {f.conflicts.map((c, i) => (
                    <p key={i} className="text-[10px]" style={{ color: "var(--color-text-secondary)" }}>
                      <span className="font-medium">{c.column}</span>: {c.description}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div className="flex gap-2">
            <button onClick={() => setStep(1)} className="text-xs px-3 py-1.5" style={{ color: "var(--color-text-muted)" }}>Back</button>
            <button onClick={() => setStep(3)} className="text-xs font-medium px-4 py-1.5 text-white" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>Confirm Import</button>
          </div>
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 3 && (
        <div className="border p-4 space-y-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          <h3 className="text-sm font-semibold">Confirm Import</h3>
          <div className="space-y-1.5">
            <p className="text-xs"><span style={{ color: "var(--color-text-muted)" }}>Patient:</span> {patientName}</p>
            {patientEmail && <p className="text-xs"><span style={{ color: "var(--color-text-muted)" }}>Email:</span> {patientEmail}</p>}
            <div className="mt-2">
              {files.map((f) => (
                <div key={f.file_id} className="flex items-center gap-2 py-1">
                  <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase" style={{ background: dtColor(f.detected_data_type).bg, color: dtColor(f.detected_data_type).text, borderRadius: "2px" }}>{f.detected_data_type}</span>
                  <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{f.filename}</span>
                  <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{f.row_count} rows</span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStep(2)} className="text-xs px-3 py-1.5" style={{ color: "var(--color-text-muted)" }}>Back</button>
            <button onClick={confirmImport} disabled={importing} className="text-xs font-medium px-4 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
              {importing ? "Importing..." : "Import Data"}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Done */}
      {step === 4 && importResult && (
        <div className="border p-4 space-y-3" style={{ borderColor: "var(--color-success)", background: "var(--color-success-bg)", borderRadius: "3px" }}>
          <h3 className="text-sm font-semibold" style={{ color: "var(--color-success)" }}>Import Complete</h3>
          <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
            Patient <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>{patientName}</span> has been created.
          </p>
          <div className="space-y-1">
            {importResult.results.map((r) => (
              <div key={r.file_id} className="flex items-center gap-2 text-[10px]">
                <span className="font-medium px-1.5 py-0.5 uppercase" style={{ background: dtColor(r.data_type).bg, color: dtColor(r.data_type).text, borderRadius: "2px" }}>{r.data_type}</span>
                <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-secondary)" }}>{r.imported} rows imported</span>
                {r.errors > 0 && <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-severity-concerning)" }}>{r.errors} errors</span>}
              </div>
            ))}
          </div>
          <div className="flex gap-2 pt-2">
            <a href={`/clinician/patient/${importResult.patient_id}`} className="text-xs font-medium px-4 py-1.5 text-white" style={{ background: "var(--color-accent-primary)", borderRadius: "3px", textDecoration: "none" }}>View Patient</a>
            <a href="/clinician" className="text-xs px-3 py-1.5" style={{ color: "var(--color-text-muted)", textDecoration: "none" }}>Back to Roster</a>
          </div>
          <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-border-light)" }}>
            <p className="text-[10px] font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Next steps:</p>
            <p className="text-[10px]" style={{ color: "var(--color-text-secondary)" }}>Upload bloodwork PDFs from the patient's Docs tab for full extraction and analysis.</p>
          </div>
        </div>
      )}
    </div>
  );
}
