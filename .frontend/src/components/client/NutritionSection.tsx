"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
    <div className="space-y-3">
      {current && (() => {
        const macros = [
          { label: "Protein", g: current.protein_g, color: "#E5534B", pct: Math.round(current.protein_g * 4 / current.calories * 100) },
          { label: "Carbs", g: current.carbs_g, color: "#D4952A", pct: Math.round(current.carbs_g * 4 / current.calories * 100) },
          { label: "Fat", g: current.fat_g, color: "#4C8DFF", pct: Math.round(current.fat_g * 9 / current.calories * 100) },
        ];
        return (
          <div className="border p-4" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="text-xl font-semibold" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{current.calories}</span>
              <span className="text-[10px] uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>kcal/day</span>
              <span className="text-[10px] ml-auto" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>Since {formatDate(current.effective_date)}</span>
            </div>
            <div className="flex overflow-hidden h-1.5 mb-3" style={{ background: "var(--color-border-light)", borderRadius: "1px" }}>
              {macros.map((m) => (<div key={m.label} style={{ width: `${m.pct}%`, background: m.color }} />))}
            </div>
            <div className="grid grid-cols-3 gap-3">
              {macros.map((m) => (
                <div key={m.label} className="text-center">
                  <p className="text-base font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace", color: m.color }}>{m.g}g</p>
                  <p className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{m.label} ({m.pct}%)</p>
                </div>
              ))}
            </div>
            {current.notes && <p className="text-xs mt-2" style={{ color: "var(--color-text-secondary)" }}>{current.notes}</p>}
          </div>
        );
      })()}
      <button onClick={() => setShowForm(!showForm)} className="text-[10px] font-medium px-3 py-1.5" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "3px" }}>{showForm ? "Cancel" : "Update Targets"}</button>
      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="p-3 border space-y-2" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Calories</label><input type="number" value={cal} onChange={(e) => setCal(e.target.value)} placeholder={String(current?.calories || "")} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Protein (g)</label><input type="number" value={pro} onChange={(e) => setPro(e.target.value)} placeholder={String(current?.protein_g || "")} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Carbs (g)</label><input type="number" value={carb} onChange={(e) => setCarb(e.target.value)} placeholder={String(current?.carbs_g || "")} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Fat (g)</label><input type="number" value={fat} onChange={(e) => setFat(e.target.value)} placeholder={String(current?.fat_g || "")} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
              </div>
              <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Effective Date</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
              <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Notes</label><textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full text-xs px-2 py-1.5 border resize-none" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
              <button onClick={handleSave} disabled={!cal || !pro || !carb || !fat || !date} className="text-xs font-medium px-3 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>Save</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
