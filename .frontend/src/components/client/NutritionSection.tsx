"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { NutritionTarget } from "@/lib/types";
import { formatDate } from "@/lib/formatters";

interface NutritionSectionProps {
  nutrition: NutritionTarget[];
  onSave: (text: string, action: () => Promise<void>) => void;
  saveNutrition: (target: { calories: number; protein_g: number; carbs_g: number; fat_g: number; effective_date: string; notes?: string }) => Promise<void>;
}

export default function NutritionSection({ nutrition, onSave, saveNutrition }: NutritionSectionProps) {
  const [showForm, setShowForm] = useState(false);
  const [cal, setCal] = useState(""); const [pro, setPro] = useState(""); const [carb, setCarb] = useState(""); const [fat, setFat] = useState(""); const [date, setDate] = useState(""); const [notes, setNotes] = useState("");

  const current = nutrition[0];
  const handleSave = () => {
    if (!cal || !pro || !carb || !fat || !date) return;
    const text = `Set nutrition targets effective ${date}: ${cal} kcal — ${pro}g protein, ${carb}g carbs, ${fat}g fat.${notes ? ` Notes: ${notes}.` : ""}`;
    onSave(text, async () => {
      await saveNutrition({ calories: +cal, protein_g: +pro, carbs_g: +carb, fat_g: +fat, effective_date: date, notes: notes || undefined });
      setShowForm(false); setCal(""); setPro(""); setCarb(""); setFat(""); setDate(""); setNotes("");
    });
  };

  return (
    <div className="space-y-4">
      {current && (() => {
        const macros = [
          { label: "Protein", g: current.protein_g, color: "#C44536", pct: Math.round(current.protein_g * 4 / current.calories * 100) },
          { label: "Carbs", g: current.carbs_g, color: "#C98B2F", pct: Math.round(current.carbs_g * 4 / current.calories * 100) },
          { label: "Fat", g: current.fat_g, color: "#4A7FA5", pct: Math.round(current.fat_g * 9 / current.calories * 100) },
        ];
        return (
          <div className="rounded-xl p-5 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="text-2xl font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{current.calories}</span>
              <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>kcal/day</span>
              <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>Since {formatDate(current.effective_date)}</span>
            </div>
            <div className="flex rounded-full overflow-hidden h-3 mb-3">{macros.map((m) => (<div key={m.label} style={{ width: `${m.pct}%`, background: m.color }} />))}</div>
            <div className="grid grid-cols-3 gap-3">
              {macros.map((m) => (<div key={m.label} className="text-center"><p className="text-lg font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace", color: m.color }}>{m.g}g</p><p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{m.label} ({m.pct}%)</p></div>))}
            </div>
            {current.notes && <p className="text-xs mt-3" style={{ color: "var(--color-text-secondary)" }}>{current.notes}</p>}
          </div>
        );
      })()}
      <button onClick={() => setShowForm(!showForm)} className="text-xs font-medium px-4 py-2 rounded-lg" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}>{showForm ? "Cancel" : "Update Targets"}</button>
      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="p-4 rounded-xl border space-y-3" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-primary)" }}>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Calories</label><input type="number" value={cal} onChange={(e) => setCal(e.target.value)} placeholder={String(current?.calories || "")} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} /></div>
                <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Protein (g)</label><input type="number" value={pro} onChange={(e) => setPro(e.target.value)} placeholder={String(current?.protein_g || "")} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} /></div>
                <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Carbs (g)</label><input type="number" value={carb} onChange={(e) => setCarb(e.target.value)} placeholder={String(current?.carbs_g || "")} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} /></div>
                <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Fat (g)</label><input type="number" value={fat} onChange={(e) => setFat(e.target.value)} placeholder={String(current?.fat_g || "")} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} /></div>
              </div>
              <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Effective Date</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} /></div>
              <div><label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Notes</label><textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full text-sm px-3 py-2 rounded-lg border resize-none" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} /></div>
              <button onClick={handleSave} disabled={!cal || !pro || !carb || !fat || !date} className="text-sm font-medium px-4 py-2 rounded-lg text-white disabled:opacity-50" style={{ background: "var(--color-accent-primary)" }}>Save Targets</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
