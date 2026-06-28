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
    <div className="flex border-b mb-5" style={{ borderColor: "var(--color-border-light)" }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className="px-3 py-2 text-xs font-medium tracking-wide uppercase transition-colors"
          style={{
            color: activeTab === tab.id ? "var(--color-accent-primary)" : "var(--color-text-muted)",
            borderBottom: activeTab === tab.id ? "2px solid var(--color-accent-primary)" : "2px solid transparent",
            marginBottom: "-1px",
          }}
        >
          {tab.label}
          {tab.badge != null && tab.badge > 0 && (
            <span
              className="ml-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-sm"
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
