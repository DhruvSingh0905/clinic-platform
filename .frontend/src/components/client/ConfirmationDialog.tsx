"use client";

import { motion, AnimatePresence } from "framer-motion";

interface ConfirmationDialogProps {
  pending: { text: string; onConfirm: () => Promise<void> } | null;
  submitting: boolean;
  onCancel: () => void;
}

export default function ConfirmationDialog({ pending, submitting, onCancel }: ConfirmationDialogProps) {
  return (
    <AnimatePresence>
      {pending && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(26, 24, 22, 0.5)", backdropFilter: "blur(4px)" }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 10 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 10 }}
            className="w-[440px] rounded-xl p-6"
            style={{ background: "var(--color-bg-card)", boxShadow: "var(--shadow-elevated)", border: "1px solid var(--color-border-card)" }}
          >
            <h3 className="text-base font-semibold mb-1" style={{ fontFamily: "'Crimson Pro', serif" }}>Confirm Action</h3>
            <p className="text-xs mb-4" style={{ color: "var(--color-text-muted)" }}>Review what will be committed:</p>
            <div className="rounded-lg p-3 mb-5" style={{ background: "var(--color-bg-secondary)", fontFamily: "'IBM Plex Mono', monospace", fontSize: "13px", lineHeight: "1.5", color: "var(--color-text-primary)" }}>
              {pending.text}
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={onCancel} className="text-sm px-4 py-2 rounded-lg" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
              <button
                onClick={async () => { await pending.onConfirm(); onCancel(); }}
                disabled={submitting}
                className="text-sm font-medium px-5 py-2 rounded-lg text-white disabled:opacity-50"
                style={{ background: "var(--color-accent-primary)" }}
              >
                {submitting ? "Committing..." : "Confirm & Commit"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
