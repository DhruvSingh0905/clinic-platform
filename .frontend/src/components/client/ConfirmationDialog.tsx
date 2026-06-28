"use client";

import { AnimatePresence, motion } from "framer-motion";

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
          style={{ background: "var(--color-bg-overlay)" }}
        >
          <motion.div
            initial={{ scale: 0.98 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0.98 }}
            className="w-[440px] border p-5"
            style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-emphasis)", borderRadius: "4px" }}
          >
            <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--color-text-primary)" }}>Confirm Action</h3>
            <p className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>Review what will be committed:</p>
            <div
              className="p-3 mb-4 text-xs leading-relaxed"
              style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border-light)", borderRadius: "3px", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)" }}
            >
              {pending.text}
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={onCancel} className="text-xs px-3 py-1.5" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
              <button
                onClick={async () => { await pending.onConfirm(); onCancel(); }}
                disabled={submitting}
                className="text-xs font-medium px-4 py-1.5 disabled:opacity-50"
                style={{ background: "var(--color-accent-primary)", color: "#fff", borderRadius: "3px" }}
              >
                {submitting ? "Committing..." : "Confirm"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
