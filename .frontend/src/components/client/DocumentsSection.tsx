"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
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
  athleteId: string;
}

export default function DocumentsSection({ athleteId }: DocumentsSectionProps) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/coach/coach-001/client/${athleteId}/documents`)
      .then((r) => r.json())
      .then((d) => setDocs(d.documents || []))
      .catch(() => {});
  }, [athleteId]);

  return (
    <div className="space-y-4">
      {docs.length === 0 && (
        <div className="text-center py-12">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" className="mx-auto mb-3">
            <rect x="8" y="4" width="24" height="32" rx="2" /><path d="M14 12h12M14 18h12M14 24h8" />
          </svg>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>No documents uploaded yet</p>
          <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>Bloodwork PDFs will appear here after upload</p>
        </div>
      )}

      {docs.length > 0 && !selectedDoc && (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
          {docs.map((doc, i) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
            >
              {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-card)" }} />}
              <div className="px-4 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--color-severity-concerning-bg)" }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-severity-concerning)" strokeWidth="1.5">
                    <rect x="3" y="1" width="10" height="14" rx="1" /><path d="M6 5h4M6 8h4M6 11h2" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium" style={{ color: "var(--color-text-primary)" }}>
                    {doc.source_type === "LAB_PDF" ? "Bloodwork" : doc.source_type}
                    {doc.draw_date && <span className="ml-2 font-normal" style={{ color: "var(--color-text-muted)" }}>· Draw date: {formatDate(doc.draw_date)}</span>}
                  </p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Uploaded {formatDate(doc.uploaded_at)}</p>
                </div>
                {doc.has_file && (
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => setSelectedDoc(doc.id)}
                      className="text-xs font-medium px-3 py-1.5 rounded-lg"
                      style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}
                    >
                      View
                    </button>
                    <a
                      href={`${API_BASE}/api/coach/coach-001/client/${athleteId}/documents/${doc.id}`}
                      download
                      className="text-xs font-medium px-3 py-1.5 rounded-lg"
                      style={{ background: "var(--color-bg-secondary)", color: "var(--color-text-secondary)" }}
                    >
                      Download
                    </a>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {selectedDoc && (
        <div>
          <button
            onClick={() => setSelectedDoc(null)}
            className="text-xs mb-3 flex items-center gap-1"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11L5 7l4-4" /></svg>
            Back to documents
          </button>
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
            <iframe
              src={`${API_BASE}/api/coach/coach-001/client/${athleteId}/documents/${selectedDoc}`}
              className="w-full"
              style={{ height: "70vh", border: "none" }}
              title="Document viewer"
            />
          </div>
        </div>
      )}
    </div>
  );
}
