import { Activity, FileClock, MonitorDot, ShieldCheck } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"


const navigation = [
  { to: "/", label: "Live Training", icon: Activity, end: true },
  { to: "/history", label: "Session History", icon: FileClock, end: false },
]


export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-lockup">
          <div className="brand-symbol" aria-hidden="true">
            <Activity size={21} strokeWidth={2.2} />
          </div>
          <div>
            <strong>LiteRehab</strong>
            <span>Fusion workspace</span>
          </div>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
              end={end}
              key={to}
              to={to}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-note">
          <div className="sidebar-note-title">
            <ShieldCheck size={16} />
            <span>Local only</span>
          </div>
          <p>Session data remains on this presentation computer.</p>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="workspace-bar">
          <div className="workspace-status">
            <MonitorDot size={16} />
            <span>Offline classroom demo</span>
          </div>
          <p>Engineering prototype · Not a medical device</p>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
