"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden" style={{ background: "#1A1816" }}>
      {/* Noise texture */}
      <div className="noise-overlay absolute inset-0" />

      {/* Animated gradient sweep */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          background: "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(193, 122, 47, 0.15) 0%, transparent 70%)",
        }}
      />
      <motion.div
        className="absolute inset-0"
        animate={{
          background: [
            "radial-gradient(ellipse 60% 40% at 30% 50%, rgba(193, 122, 47, 0.08) 0%, transparent 70%)",
            "radial-gradient(ellipse 60% 40% at 70% 50%, rgba(193, 122, 47, 0.08) 0%, transparent 70%)",
            "radial-gradient(ellipse 60% 40% at 30% 50%, rgba(193, 122, 47, 0.08) 0%, transparent 70%)",
          ],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Content */}
      <div className="relative z-10 max-w-3xl mx-auto px-6 text-center">
        {/* Monogram */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mb-8"
        >
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl"
            style={{
              background: "linear-gradient(135deg, rgba(193, 122, 47, 0.2) 0%, rgba(193, 122, 47, 0.05) 100%)",
              border: "1px solid rgba(193, 122, 47, 0.3)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path
                d="M14 2C7.373 2 2 7.373 2 14s5.373 12 12 12 12-5.373 12-12S20.627 2 14 2z"
                stroke="rgba(193, 122, 47, 0.8)"
                strokeWidth="1.5"
                fill="none"
              />
              <path
                d="M9 14.5C9 11.462 11.462 9 14.5 9"
                stroke="rgba(193, 122, 47, 0.6)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <circle cx="14" cy="14" r="2" fill="rgba(193, 122, 47, 0.8)" />
            </svg>
          </div>
        </motion.div>

        {/* Heading */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="text-5xl md:text-6xl font-semibold tracking-tight mb-4"
          style={{ fontFamily: "'Crimson Pro', serif", color: "#FAFAF7" }}
        >
          Coach Platform
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="text-lg md:text-xl mb-16 tracking-wide"
          style={{ fontFamily: "'Outfit', sans-serif", color: "#9B948D", letterSpacing: "0.02em" }}
        >
          Domain-aware client data for physique coaches
        </motion.p>

        {/* Role cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {/* Coach Card */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            onClick={() => router.push("/coach")}
            className="group cursor-pointer rounded-2xl p-8 text-left"
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              transition: "border-color 0.3s ease, box-shadow 0.3s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(193, 122, 47, 0.4)";
              e.currentTarget.style.boxShadow = "0 8px 32px rgba(193, 122, 47, 0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.06)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            {/* Icon */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
              style={{ background: "rgba(193, 122, 47, 0.1)" }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(193, 122, 47, 0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>

            <h2
              className="text-xl font-medium mb-2"
              style={{ fontFamily: "'Crimson Pro', serif", color: "#FAFAF7" }}
            >
              Coach
            </h2>
            <p
              className="text-sm mb-6 leading-relaxed"
              style={{ color: "#9B948D" }}
            >
              Ranked roster queue, client deep-dives, training and nutrition management
            </p>

            <div
              className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg"
              style={{
                background: "rgba(193, 122, 47, 0.12)",
                color: "#C17A2F",
              }}
            >
              Enter as Coach
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 8h10M9 4l4 4-4 4" />
              </svg>
            </div>
          </motion.div>

          {/* Athlete Card */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.55 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            onClick={() => router.push("/athlete")}
            className="group cursor-pointer rounded-2xl p-8 text-left"
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              transition: "border-color 0.3s ease, box-shadow 0.3s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(90, 138, 92, 0.4)";
              e.currentTarget.style.boxShadow = "0 8px 32px rgba(90, 138, 92, 0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.06)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            {/* Icon */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
              style={{ background: "rgba(90, 138, 92, 0.1)" }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(90, 138, 92, 0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>

            <h2
              className="text-xl font-medium mb-2"
              style={{ fontFamily: "'Crimson Pro', serif", color: "#FAFAF7" }}
            >
              Athlete
            </h2>
            <p
              className="text-sm mb-6 leading-relaxed"
              style={{ color: "#9B948D" }}
            >
              Personal dashboard, wearable trends, substance logging, your own data
            </p>

            <div
              className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg"
              style={{
                background: "rgba(90, 138, 92, 0.12)",
                color: "#5A8A5C",
              }}
            >
              Enter as Athlete
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 8h10M9 4l4 4-4 4" />
              </svg>
            </div>
          </motion.div>
        </div>

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.8 }}
          className="mt-16 text-xs tracking-widest uppercase"
          style={{ color: "#6B6560", letterSpacing: "0.15em" }}
        >
          Cycle Data Platform
        </motion.p>
      </div>
    </div>
  );
}
