"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { sendClinicianChat, sendPatientChat } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatProps {
  role: "clinician" | "patient";
  patientId: string;
  clinicianId?: string;
  patientName?: string;
  onClose: () => void;
}

export default function Chat({ role, patientId, clinicianId, patientName, onClose }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      let response: string;
      if (role === "clinician" && clinicianId) {
        response = await sendClinicianChat(clinicianId, patientId, userMsg.content);
      } else {
        response = await sendPatientChat(patientId, userMsg.content);
      }
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: response }]);
    } catch {
      setMessages((prev) => [...prev, { id: `e-${Date.now()}`, role: "assistant", content: "Failed to get response." }]);
    }
    setLoading(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.15 }}
      className="fixed bottom-3 right-3 w-[400px] max-h-[min(520px,calc(100vh-1.5rem))] flex flex-col overflow-hidden z-50"
      style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-emphasis)", borderRadius: "4px" }}
    >
      {/* Header */}
      <div className="shrink-0 border-b" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)" }}>
        <div className="flex items-center justify-between px-4 py-2.5">
          <p className="text-xs font-semibold" style={{ color: "var(--color-text-primary)" }}>
            {role === "clinician" ? `Chat — ${patientName || "Patient"}` : "Chat — Your Data"}
          </p>
          <button onClick={onClose} className="p-1 hover:opacity-70" style={{ color: "var(--color-text-muted)" }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M3 3l8 8M11 3l-8 8" /></svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2" style={{ background: "var(--color-bg-primary)" }}>
        {messages.length === 0 && (
          <p className="text-xs py-8 text-center" style={{ color: "var(--color-text-muted)" }}>
            {role === "clinician"
              ? "Ask about this patient's data, trends, or labs. You can also manage training, nutrition, and recovery."
              : "Ask about your health data, compounds, or trends. You can manage your stack and calendar."}
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className="max-w-[85%] px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap"
              style={
                msg.role === "user"
                  ? { background: "var(--color-accent-primary)", color: "#fff", borderRadius: "4px 4px 1px 4px" }
                  : { background: "var(--color-bg-card)", border: "1px solid var(--color-border-light)", color: "var(--color-text-primary)", borderRadius: "4px 4px 4px 1px" }
              }
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="px-3 py-2" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-light)", borderRadius: "4px" }}>
              <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>Thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-3 py-2 border-t" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)" }}>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={role === "clinician" ? "Ask about patient data..." : "Ask about your data..."}
            className="flex-1 text-xs px-3 py-2 border"
            style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px", outline: "none" }}
            disabled={loading}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="px-3 py-2 text-xs font-medium disabled:opacity-30"
            style={{ background: "var(--color-accent-primary)", color: "#fff", borderRadius: "3px" }}
          >
            Send
          </button>
        </div>
      </div>
    </motion.div>
  );
}
