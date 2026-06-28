"use client";

import { useState, useEffect } from "react";
import { formatDate } from "@/lib/formatters";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Document {
  id: number;
  source_type: string;
  uploaded_at: string;
  draw_date: string | null;
  has_file: boolean;
}

interface DocumentsSectionProps {
  patientId: string;
}

export default function DocumentsSection({ patientId }: DocumentsSectionProps) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/clinician/clinician-001/patient/${patientId}/documents`)
      .then((r) => r.json())
      .then((d) => setDocs(d.documents || []))
      .catch(() => {});
  }, [patientId]);

  return (
    <div className="space-y-3">
      {docs.length === 0 && (
        <div className="text-center py-8">
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>No documents uploaded yet</p>
          <p className="text-[10px] mt-0.5" style={{ color: "var(--color-text-muted)" }}>Bloodwork PDFs will appear here</p>
        </div>
      )}

      {docs.length > 0 && !selectedDoc && (
        <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          {docs.map((doc, i) => (
            <div key={doc.id}>
              {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-light)" }} />}
              <div className="px-3 py-2.5 flex items-center gap-3 data-row">
                <div className="w-6 h-6 flex items-center justify-center shrink-0" style={{ background: "var(--color-severity-concerning-bg)", borderRadius: "2px" }}>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--color-severity-concerning)" strokeWidth="1.2"><rect x="2" y="1" width="8" height="10" rx="1" /><path d="M4 4h4M4 6h4M4 8h2" /></svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium" style={{ color: "var(--color-text-primary)" }}>
                    {doc.source_type === "LAB_PDF" ? "Bloodwork" : doc.source_type}
                    {doc.draw_date && <span className="ml-2 font-normal" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>· {formatDate(doc.draw_date)}</span>}
                  </p>
                  <p className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>Uploaded {formatDate(doc.uploaded_at)}</p>
                </div>
                {doc.has_file && (
                  <div className="flex gap-1.5 shrink-0">
                    <button onClick={() => setSelectedDoc(doc.id)} className="text-[10px] font-medium px-2 py-1" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "2px" }}>View</button>
                    <a href={`${API_BASE}/api/clinician/clinician-001/patient/${patientId}/documents/${doc.id}`} download className="text-[10px] font-medium px-2 py-1" style={{ background: "var(--color-bg-hover)", color: "var(--color-text-secondary)", borderRadius: "2px" }}>Download</a>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedDoc && (
        <div>
          <button onClick={() => setSelectedDoc(null)} className="text-[10px] mb-2 flex items-center gap-1" style={{ color: "var(--color-text-muted)" }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M7 8L3 5l4-3" /></svg>
            Back
          </button>
          <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", borderRadius: "3px" }}>
            <iframe src={`${API_BASE}/api/clinician/clinician-001/patient/${patientId}/documents/${selectedDoc}`} className="w-full" style={{ height: "70vh", border: "none" }} title="Document viewer" />
          </div>
        </div>
      )}
    </div>
  );
}
