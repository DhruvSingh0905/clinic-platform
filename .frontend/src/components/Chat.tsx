"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { sendCoachChat, sendAthleteChat } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatProps {
  role: "coach" | "athlete";
  athleteId: string;
  coachId?: string;
  athleteName?: string;
  findingId?: string;
  onClose: () => void;
}

export default function Chat({ role, athleteId, coachId, athleteName, findingId, onClose }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      let response: string;
      if (role === "coach" && coachId) {
        response = await sendCoachChat(coachId, athleteId, userMsg.content, findingId);
      } else {
        response = await sendAthleteChat(athleteId, userMsg.content, findingId);
      }
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: response }]);
    } catch {
      setMessages((prev) => [...prev, { id: `e-${Date.now()}`, role: "assistant", content: "Failed to get response. Please try again." }]);
    }
    setLoading(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className="fixed bottom-4 right-4 w-[400px] max-h-[min(520px,calc(100vh-2rem))] rounded-2xl flex flex-col overflow-hidden z-50"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border-card)",
        boxShadow: "0 16px 48px rgba(26, 24, 22, 0.2), 0 4px 12px rgba(26, 24, 22, 0.1)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3.5 shrink-0"
        style={{ background: "var(--color-bg-sidebar)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--color-text-sidebar-active)", fontFamily: "'Crimson Pro', serif" }}>
            {role === "coach" ? `Chat — ${athleteName || "Client"}` : "Chat — Your Data"}
          </p>
          {findingId && (
            <p className="text-xs mt-0.5" style={{ color: "var(--color-accent-primary)" }}>Finding thread</p>
          )}
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:opacity-70 transition-opacity" style={{ color: "var(--color-text-sidebar)" }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3" style={{ background: "var(--color-bg-primary)" }}>
        {messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {role === "coach"
                ? "Ask about this client's data, trends, or findings. You can also manage training, nutrition, and recovery."
                : "Ask about your health data, compounds, or findings. You can manage your stack and calendar."}
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className="max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
              style={
                msg.role === "user"
                  ? { background: "var(--color-accent-primary)", color: "white", borderBottomRightRadius: "4px" }
                  : { background: "var(--color-bg-card)", border: "1px solid var(--color-border-card)", color: "var(--color-text-primary)", borderBottomLeftRadius: "4px", boxShadow: "var(--shadow-card)" }
              }
            >
              {msg.content}
            </div>
          </motion.div>
        ))}

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
            <div className="rounded-xl px-4 py-3" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-card)" }}>
              <div className="flex gap-1.5">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 rounded-full"
                    style={{
                      background: "var(--color-text-muted)",
                      animation: `typingBounce 0.6s ease-in-out ${i * 0.15}s infinite`,
                    }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 py-3 border-t" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={role === "coach" ? "Ask about client data..." : "Ask about your data..."}
            className="flex-1 text-sm px-3.5 py-2.5 rounded-lg border"
            style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", outline: "none" }}
            disabled={loading}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 rounded-lg text-sm font-medium disabled:opacity-40 transition-opacity"
            style={{ background: "var(--color-accent-primary)", color: "white" }}
          >
            Send
          </button>
        </div>
      </div>
    </motion.div>
  );
}
