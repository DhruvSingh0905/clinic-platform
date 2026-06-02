"use client";

interface Tab {
  id: string;
  label: string;
  badge?: number;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
}

export default function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="flex gap-1 border-b pb-px mb-6" style={{ borderColor: "var(--color-border-light)" }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className="relative px-4 py-2.5 text-sm font-medium transition-colors rounded-t-lg"
          style={{
            color: activeTab === tab.id ? "var(--color-accent-primary)" : "var(--color-text-muted)",
            background: activeTab === tab.id ? "var(--color-bg-card)" : "transparent",
            borderBottom: activeTab === tab.id ? "2px solid var(--color-accent-primary)" : "2px solid transparent",
          }}
        >
          {tab.label}
          {tab.badge != null && tab.badge > 0 && (
            <span
              className="ml-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full"
              style={{ background: "var(--color-severity-concerning-bg)", color: "var(--color-severity-concerning)" }}
            >
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
