"use client";

interface SidebarProps {
  activePage?: "roster" | "client" | "onboard";
}

export default function Sidebar({ activePage = "roster" }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-48 flex flex-col z-30 border-r" style={{ background: "var(--color-bg-sidebar)", borderColor: "var(--color-border-light)" }}>
      <div className="px-4 py-4 border-b" style={{ borderColor: "var(--color-border-light)" }}>
        <h1 className="text-sm font-semibold" style={{ color: "var(--color-text-sidebar-active)" }}>Clinic Platform</h1>
        <p className="text-[10px]" style={{ color: "var(--color-text-sidebar)" }}>TRT/HRT Management</p>
      </div>
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        <a
          href="/clinician"
          className={`sidebar-link ${activePage === "roster" || activePage === "client" ? "active" : ""} flex items-center gap-2 px-2.5 py-2 rounded text-xs`}
          style={{ color: activePage === "roster" || activePage === "client" ? "var(--color-text-sidebar-active)" : "var(--color-text-sidebar)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M10 12v-1a2.5 2.5 0 0 0-2.5-2.5H5A2.5 2.5 0 0 0 2.5 11v1" /><circle cx="6.25" cy="4.5" r="2.5" /></svg>
          Roster
        </a>
        <a
          href="/clinician/onboard"
          className={`sidebar-link ${activePage === "onboard" ? "active" : ""} flex items-center gap-2 px-2.5 py-2 rounded text-xs`}
          style={{ color: activePage === "onboard" ? "var(--color-text-sidebar-active)" : "var(--color-text-sidebar)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M7 1v12M1 7h12" /></svg>
          Onboard
        </a>
      </nav>
      <div className="px-3 py-3 border-t" style={{ borderColor: "var(--color-border-light)" }}>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-medium" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}>DC</div>
          <div>
            <p className="text-[10px] font-medium" style={{ color: "var(--color-text-sidebar-active)" }}>Demo Clinician</p>
            <p className="text-[9px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-sidebar)" }}>clinician-001</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
