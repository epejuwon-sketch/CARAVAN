import React from "react";
import {
  LayoutDashboard,
  Compass,
  FolderKanban,
  User,
  Settings,
  ShieldCheck,
  Bell,
  LogOut,
  Users,
  CheckCircle2,
  BarChart3,
} from "lucide-react";
import { useAuth } from "../../lib/auth";
import { CaravanLogo } from "../brand/CaravanLogo";

interface PortalLayoutProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
  children: React.ReactNode;
}

export const PortalLayout: React.FC<PortalLayoutProps> = ({
  currentRoute,
  onNavigate,
  children,
}) => {
  const { user, logout } = useAuth();

  const isAdmin = ["ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "OPPORTUNITY_REVIEWER"].includes(
    user?.role || ""
  );

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "JD";

  return (
    <div className="app-shell">
      {/* Left Sidebar matching Screen 2 of approved reference */}
      <aside className="app-sidebar">
        <div>
          {/* Logo */}
          <CaravanLogo
            size={26}
            wordmarkColor="white"
            onClick={() => onNavigate("dashboard")}
          />

          {/* Navigation Links */}
          <nav className="sidebar-nav">
            <button
              type="button"
              className={`sidebar-link ${currentRoute === "dashboard" ? "active" : ""}`}
              style={
                currentRoute === "dashboard"
                  ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                  : undefined
              }
              onClick={() => onNavigate("dashboard")}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </button>

            <button
              type="button"
              className={`sidebar-link ${currentRoute === "discover" ? "active" : ""}`}
              style={
                currentRoute === "discover"
                  ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                  : undefined
              }
              onClick={() => onNavigate("discover")}
            >
              <Compass size={18} />
              <span>Opportunities</span>
            </button>

            <button
              type="button"
              className={`sidebar-link ${currentRoute === "applications" ? "active" : ""}`}
              style={
                currentRoute === "applications"
                  ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                  : undefined
              }
              onClick={() => onNavigate("applications")}
            >
              <FolderKanban size={18} />
              <span>Applications</span>
            </button>

            <button
              type="button"
              className={`sidebar-link ${currentRoute === "account" ? "active" : ""}`}
              style={
                currentRoute === "account"
                  ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                  : undefined
              }
              onClick={() => onNavigate("account")}
            >
              <User size={18} />
              <span>Profile</span>
            </button>

            <button
              type="button"
              className={`sidebar-link ${
                currentRoute === "billing" || currentRoute === "support" ? "active" : ""
              }`}
              style={
                currentRoute === "billing" || currentRoute === "support"
                  ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                  : undefined
              }
              onClick={() => onNavigate("billing")}
            >
              <Settings size={18} />
              <span>Settings</span>
            </button>

            {isAdmin && (
              <div
                style={{
                  marginTop: 24,
                  paddingTop: 16,
                  borderTop: "1px solid var(--border-subtle)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    paddingLeft: 14,
                    marginBottom: 4,
                  }}
                >
                  Admin
                </div>
                <button
                  type="button"
                  className={`sidebar-link ${currentRoute === "admin" ? "active" : ""}`}
                  style={
                    currentRoute === "admin"
                      ? { backgroundColor: "#C69D49", color: "#000000", fontWeight: 700 }
                      : undefined
                  }
                  onClick={() => onNavigate("admin")}
                >
                  <ShieldCheck size={18} />
                  <span>Admin Portal</span>
                </button>
              </div>
            )}
          </nav>
        </div>

        {/* Bottom Sign Out */}
        <div style={{ paddingTop: 16, borderTop: "1px solid var(--border-subtle)" }}>
          <button
            type="button"
            className="sidebar-link"
            style={{ width: "100%", justifyContent: "flex-start", color: "var(--text-secondary)" }}
            onClick={() => {
              if (logout) logout();
              onNavigate("home");
            }}
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <div className="app-main">
        {/* Topbar with Bell and JD avatar */}
        <header className="app-topbar">
          <div className="row" style={{ gap: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)" }}>
              CARAVAN PLATFORM
            </span>
          </div>

          <div className="row" style={{ gap: 14 }}>
            <button
              type="button"
              style={{
                width: 36,
                height: 36,
                borderRadius: "var(--radius-full)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-card)",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                position: "relative",
              }}
              title="Notifications"
            >
              <Bell size={17} />
              <span
                style={{
                  position: "absolute",
                  top: 7,
                  right: 7,
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  backgroundColor: "var(--accent-gold)",
                }}
              />
            </button>

            {/* Avatar JD */}
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "var(--radius-full)",
                backgroundColor: "#161616",
                border: "1.5px solid var(--accent-gold)",
                color: "var(--accent-gold-bright)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer",
              }}
              title={user?.full_name || "John Doe"}
            >
              {initials}
            </div>
          </div>
        </header>

        {/* Content Body */}
        <div className="app-body">
          {children}
        </div>
      </div>
    </div>
  );
};
