"use client";

import Sidebar from "@/components/Sidebar";
import OnboardWizard from "@/components/onboard/OnboardWizard";

export default function OnboardPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar activePage="onboard" />
      <main className="ml-48 flex-1 min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-3xl mx-auto px-6 py-6">
          <div className="mb-5">
            <h1 className="text-lg font-semibold">Onboard Patient</h1>
            <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
              Import training, nutrition, bloodwork, and protocol data from spreadsheets
            </p>
          </div>
          <OnboardWizard />
        </div>
      </main>
    </div>
  );
}
