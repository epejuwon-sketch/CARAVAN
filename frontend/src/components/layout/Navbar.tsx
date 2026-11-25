import React from "react";
import {
  Compass,
  CheckCircle2,
  FolderKanban,
  Bookmark,
  User,
  CreditCard,
  HelpCircle,
  LogOut,
  LogIn,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../../lib/auth";

interface NavbarProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentRoute, onNavigate }) => {
  const { user, logout } = useAuth();

  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 50,
      backgroundColor: "rgba(10, 13, 20, 0.85)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--border-subtle)",
    }}>
      <div className="container row-between" style={{ height: 68 }}>
        {/* Brand */}
        <div
          className="row"
          style={{ gap: 12, cursor: "pointer" }}
          onClick={() => onNavigate(user ? "discover" : "home")}
        >
          <div style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-sm)",
            background: "linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            fontSize: 18,
            color: "#050b14",
            boxShadow: "0 0 16px rgba(56, 189, 248, 0.3)",
          }}>
            C
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em", color: "#f8fafc" }}>
              CARAVAN
            </div>
            <div style={{ fontSize: 10, color: "var(--accent-cyan)", letterSpacing: "0.08em", fontWeight: 600 }}>
              FUNDING INTELLIGENCE
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav
          className="row nav-links-row"
          style={{
            gap: 8,
            overflowX: "auto",
            WebkitOverflowScrolling: "touch",
            padding: "4px 0",
            maxWidth: "100%",
            scrollbarWidth: "none",
          }}
        >
          {!user ? (
            <>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "home" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("home")}
              >
                Platform
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "how-it-works" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("how-it-works")}
              >
                How It Works
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "categories" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("categories")}
              >
                15 Categories
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "pricing" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("pricing")}
              >
                Pricing
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline"
                onClick={() => onNavigate("login")}
              >
                <LogIn size={13} /> Sign In
              </button>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => onNavigate("register")}
              >
                Get Started
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "discover" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("discover")}
              >
                <Compass size={13} /> Discover
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "eligibility" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("eligibility")}
              >
                <Sparkles size={13} /> Eligibility
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "applications" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("applications")}
              >
                <FolderKanban size={13} /> Applications
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "saved" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("saved")}
              >
                <Bookmark size={13} /> Saved
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "billing" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("billing")}
              >
                <CreditCard size={13} /> Subscriptions
              </button>
              <button
                type="button"
                className={`btn btn-sm ${currentRoute === "account" ? "btn" : "btn-secondary"}`}
                onClick={() => onNavigate("account")}
              >
                <User size={13} /> Profile
              </button>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                title="Sign out"
                onClick={() => {
                  logout();
                  onNavigate("home");
                }}
              >
                <LogOut size={13} />
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};
