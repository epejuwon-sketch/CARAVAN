import React, { useState } from "react";
import {
  Compass,
  FolderKanban,
  Bookmark,
  User,
  CreditCard,
  HelpCircle,
  LogOut,
  LogIn,
  Menu,
  X,
  LayoutDashboard,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "../../lib/auth";
import { CaravanLogo } from "../brand/CaravanLogo";

interface NavbarProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentRoute, onNavigate }) => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleNav = (route: string) => {
    onNavigate(route);
    setMobileMenuOpen(false);
  };

  // User initials for avatar badge
  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "JD";

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        backgroundColor: "rgba(5, 5, 5, 0.95)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div className="container row-between" style={{ height: 68 }}>
        {/* Brand Logo */}
        <CaravanLogo
          size={28}
          wordmarkColor="white"
          onClick={() => handleNav(user ? "dashboard" : "home")}
        />

        {/* Desktop Navigation Links */}
        <nav
          className="row nav-desktop"
          style={{
            gap: 10,
            alignItems: "center",
          }}
        >
          {!user ? (
            <>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "discover" ? "active" : ""}`}
                onClick={() => handleNav("discover")}
              >
                Opportunities
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "about" ? "active" : ""}`}
                onClick={() => handleNav("about")}
              >
                About
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "how-it-works" ? "active" : ""}`}
                onClick={() => handleNav("how-it-works")}
              >
                How It Works
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "categories" ? "active" : ""}`}
                onClick={() => handleNav("categories")}
              >
                Categories
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "pricing" ? "active" : ""}`}
                onClick={() => handleNav("pricing")}
              >
                Pricing
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "support" ? "active" : ""}`}
                onClick={() => handleNav("support")}
              >
                Help
              </button>

              <div className="row" style={{ gap: 8, marginLeft: 16 }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleNav("login")}
                >
                  <LogIn size={13} /> Sign In
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => handleNav("register")}
                >
                  Get Started
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Authenticated Customer / Admin Links */}
              <button
                type="button"
                className={`tab-btn ${currentRoute === "dashboard" ? "active" : ""}`}
                onClick={() => handleNav("dashboard")}
              >
                <LayoutDashboard size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Dashboard
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "discover" ? "active" : ""}`}
                onClick={() => handleNav("discover")}
              >
                <Compass size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Opportunities
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "applications" ? "active" : ""}`}
                onClick={() => handleNav("applications")}
              >
                <FolderKanban size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Applications
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "eligibility" ? "active" : ""}`}
                onClick={() => handleNav("eligibility")}
              >
                <CheckCircle2 size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Eligibility
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "saved" ? "active" : ""}`}
                onClick={() => handleNav("saved")}
              >
                <Bookmark size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Saved
              </button>

              {/* Admin Portal Tab */}
              {["ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "OPPORTUNITY_REVIEWER"].includes(user.role) && (
                <button
                  type="button"
                  className={`tab-btn ${currentRoute === "admin" ? "active" : ""}`}
                  onClick={() => handleNav("admin")}
                  style={{
                    color: currentRoute === "admin" ? "#050505" : "var(--accent-gold-bright)",
                    borderColor: "var(--accent-gold)",
                  }}
                >
                  <ShieldCheck size={14} style={{ marginRight: 5, verticalAlign: "middle" }} />
                  Admin
                </button>
              )}

              {/* Profile / Account Avatar & Sign Out */}
              <div className="row" style={{ gap: 12, marginLeft: 16, borderLeft: "1px solid var(--border-subtle)", paddingLeft: 16 }}>
                <div
                  className="row"
                  style={{ gap: 8, cursor: "pointer" }}
                  onClick={() => handleNav("account")}
                  title={`${user.full_name} (${user.email})`}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "var(--radius-full)",
                      backgroundColor: "var(--accent-gold)",
                      color: "#050505",
                      fontWeight: 700,
                      fontSize: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {initials}
                  </div>
                  <div className="col" style={{ display: "none" }}>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{user.full_name}</span>
                    <span className="muted" style={{ fontSize: 10 }}>{user.role}</span>
                  </div>
                </div>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    logout();
                    handleNav("home");
                  }}
                  title="Sign Out"
                >
                  <LogOut size={13} />
                </button>
              </div>
            </>
          )}
        </nav>

        {/* Mobile Hamburger Button */}
        <div className="nav-mobile-toggle">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{ padding: "8px 10px" }}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div
          style={{
            position: "fixed",
            top: 68,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(5, 5, 5, 0.98)",
            padding: "24px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 16,
            zIndex: 49,
            overflowY: "auto",
          }}
        >
          {!user ? (
            <>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "home" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("home")}
              >
                Platform
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "discover" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("discover")}
              >
                Opportunities
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "how-it-works" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("how-it-works")}
              >
                How It Works
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "categories" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("categories")}
              >
                15 Categories
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "pricing" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("pricing")}
              >
                Pricing
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "about" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("about")}
              >
                About CARAVAN
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "support" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("support")}
              >
                Help &amp; Support
              </button>

              <div className="col" style={{ gap: 10, marginTop: 16, borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
                <button
                  type="button"
                  className="btn"
                  style={{ width: "100%", justifyContent: "center" }}
                  onClick={() => handleNav("register")}
                >
                  Get Started
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ width: "100%", justifyContent: "center" }}
                  onClick={() => handleNav("login")}
                >
                  <LogIn size={14} /> Sign In
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="row" style={{ gap: 12, paddingBottom: 16, borderBottom: "1px solid var(--border-subtle)" }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: "var(--radius-full)",
                    backgroundColor: "var(--accent-gold)",
                    color: "#050505",
                    fontWeight: 700,
                    fontSize: 14,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {initials}
                </div>
                <div className="col">
                  <span style={{ fontSize: 15, fontWeight: 700 }}>{user.full_name}</span>
                  <span className="muted" style={{ fontSize: 12 }}>{user.email}</span>
                </div>
              </div>

              <button
                type="button"
                className={`tab-btn ${currentRoute === "dashboard" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("dashboard")}
              >
                <LayoutDashboard size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                Dashboard
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "discover" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("discover")}
              >
                <Compass size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                Funding Opportunities
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "applications" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("applications")}
              >
                <FolderKanban size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                My Applications
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "eligibility" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("eligibility")}
              >
                <CheckCircle2 size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                NEON Eligibility
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "saved" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("saved")}
              >
                <Bookmark size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                Saved Shortlist
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "account" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("account")}
              >
                <User size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                Organization &amp; Profile
              </button>
              <button
                type="button"
                className={`tab-btn ${currentRoute === "billing" ? "active" : ""}`}
                style={{ textAlign: "left", padding: "12px 16px" }}
                onClick={() => handleNav("billing")}
              >
                <CreditCard size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                Subscription &amp; Billing
              </button>

              {["ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "OPPORTUNITY_REVIEWER"].includes(user.role) && (
                <button
                  type="button"
                  className={`tab-btn ${currentRoute === "admin" ? "active" : ""}`}
                  style={{ textAlign: "left", padding: "12px 16px", color: "var(--accent-gold-bright)" }}
                  onClick={() => handleNav("admin")}
                >
                  <ShieldCheck size={16} style={{ marginRight: 10, verticalAlign: "middle" }} />
                  Admin Management
                </button>
              )}

              <div style={{ marginTop: "auto", paddingTop: 20, borderTop: "1px solid var(--border-subtle)" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ width: "100%", justifyContent: "center" }}
                  onClick={() => {
                    logout();
                    handleNav("home");
                  }}
                >
                  <LogOut size={14} /> Sign Out
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Style for responsive toggle */}
      <style>{`
        @media (max-width: 900px) {
          .nav-desktop { display: none !important; }
          .nav-mobile-toggle { display: block !important; }
        }
        @media (min-width: 901px) {
          .nav-desktop { display: flex !important; }
          .nav-mobile-toggle { display: none !important; }
        }
      `}</style>
    </header>
  );
};
