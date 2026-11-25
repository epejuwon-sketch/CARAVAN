import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./lib/auth";
import { Navbar } from "./components/layout/Navbar";
import { Footer } from "./components/layout/Footer";
import { HomePage } from "./pages/HomePage";
import { DashboardPage } from "./pages/DashboardPage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { PricingPage } from "./pages/PricingPage";
import { MarketplacePage } from "./pages/MarketplacePage";
import { EligibilityPage } from "./pages/EligibilityPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { SavedPage } from "./pages/SavedPage";
import { AccountPage } from "./pages/AccountPage";
import { BillingPage } from "./pages/BillingPage";
import { SupportPage } from "./pages/SupportPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import {
  HowItWorksPage,
  AboutPage,
  ContactPage,
  LegalPrivacyPage,
} from "./pages/StaticPages";
import {
  LayoutDashboard,
  Compass,
  FolderKanban,
  User,
  ShieldCheck,
  Home,
  Lock,
} from "lucide-react";

function MainContent() {
  const { user, loading } = useAuth();
  const getInitialRoute = () => {
    if (typeof window !== "undefined" && window.location.hash) {
      const hash = window.location.hash.replace("#", "").trim();
      if (hash) return hash;
    }
    return "home";
  };

  const [currentRoute, setCurrentRoute] = useState<string>(getInitialRoute);

  // If user logs in while on landing, redirect to dashboard or admin
  useEffect(() => {
    if (user && (currentRoute === "home" || currentRoute === "login" || currentRoute === "register")) {
      const target = user.role === "ADMIN" ? "admin" : "dashboard";
      setCurrentRoute(target);
      if (typeof window !== "undefined") window.location.hash = target;
    }
  }, [user]);

  // Handle URL hash or direct route
  const navigate = (route: string) => {
    setCurrentRoute(route);
    if (typeof window !== "undefined") {
      window.location.hash = route;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace("#", "").trim();
      if (hash) setCurrentRoute(hash);
    };
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "var(--bg-primary)" }}>
        <div className="muted mono" style={{ fontSize: 13, color: "var(--accent-gold-bright)" }}>
          Initializing CARAVAN Platform...
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-primary)" }}>
      <Navbar currentRoute={currentRoute} onNavigate={navigate} />

      <main style={{ flex: 1 }}>
        {currentRoute === "home" && <HomePage onNavigate={navigate} />}
        {currentRoute === "admin" && (
          user?.role === "ADMIN" ? (
            <AdminDashboardPage onNavigate={navigate} />
          ) : (
            <div className="container" style={{ paddingTop: 64, paddingBottom: 64, display: "flex", justifyContent: "center" }}>
              <div className="card" style={{ maxWidth: 540, width: "100%", textAlign: "center", padding: "48px 32px", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
                <Lock size={44} style={{ color: "var(--accent-gold)" }} />
                <h2 style={{ fontSize: 20, fontWeight: 700, color: "#FFFFFF" }}>Administrator Authorization Required</h2>
                <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                  Access to the CARAVAN Operations Portal is restricted to verified administrators under Sentinel RBAC controls.
                </p>
                <button type="button" className="btn btn-sm" onClick={() => navigate("home")}>
                  Return to Platform
                </button>
              </div>
            </div>
          )
        )}
        {currentRoute === "how-it-works" && <HowItWorksPage onNavigate={navigate} />}
        {currentRoute === "categories" && <CategoriesPage onNavigate={navigate} />}
        {currentRoute === "pricing" && <PricingPage onNavigate={navigate} />}
        {currentRoute === "about" && <AboutPage onNavigate={navigate} />}
        {currentRoute === "contact" && <ContactPage onNavigate={navigate} />}
        {currentRoute === "legal-privacy" && <LegalPrivacyPage onNavigate={navigate} />}
        {currentRoute === "login" && <LoginPage onNavigate={navigate} />}
        {currentRoute === "register" && <RegisterPage onNavigate={navigate} />}
        {currentRoute === "discover" && <MarketplacePage onNavigate={navigate} />}
        {/* Customer Authenticated Routes */}
        {["dashboard", "applications", "eligibility", "saved", "account", "billing"].includes(currentRoute) && !user ? (
          <div className="container" style={{ paddingTop: 64, paddingBottom: 64, display: "flex", justifyContent: "center" }}>
            <div className="card" style={{ maxWidth: 540, width: "100%", textAlign: "center", padding: "48px 32px", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
              <Lock size={44} style={{ color: "var(--accent-gold)" }} />
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "#FFFFFF" }}>Authentication Required</h2>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                Please sign in to access your organization workspace, applications, and saved programs.
              </p>
              <div className="row" style={{ gap: 12 }}>
                <button type="button" className="btn btn-sm" onClick={() => navigate("login")}>
                  Sign In
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => navigate("register")}>
                  Register Organization
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {currentRoute === "dashboard" && <DashboardPage onNavigate={navigate} />}
            {currentRoute === "eligibility" && <EligibilityPage onNavigate={navigate} />}
            {currentRoute === "applications" && <ApplicationsPage onNavigate={navigate} />}
            {currentRoute === "saved" && <SavedPage onNavigate={navigate} />}
            {currentRoute === "account" && <AccountPage onNavigate={navigate} />}
            {currentRoute === "billing" && <BillingPage />}
          </>
        )}
        {currentRoute === "support" && <SupportPage />}
      </main>

      <Footer onNavigate={navigate} />

      {/* Mobile Bottom Navigation Bar (Screen 12 in Reference) */}
      <nav className="mobile-bottom-nav">
        {user ? (
          <>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "dashboard" ? "active" : ""}`}
              onClick={() => navigate("dashboard")}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </button>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "discover" ? "active" : ""}`}
              onClick={() => navigate("discover")}
            >
              <Compass size={18} />
              <span>Explore</span>
            </button>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "applications" ? "active" : ""}`}
              onClick={() => navigate("applications")}
            >
              <FolderKanban size={18} />
              <span>Pipelines</span>
            </button>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "account" ? "active" : ""}`}
              onClick={() => navigate("account")}
            >
              <User size={18} />
              <span>Profile</span>
            </button>
            {user.role === "ADMIN" && (
              <button
                type="button"
                className={`mobile-nav-item ${currentRoute === "admin" ? "active" : ""}`}
                onClick={() => navigate("admin")}
              >
                <ShieldCheck size={18} />
                <span>Admin</span>
              </button>
            )}
          </>
        ) : (
          <>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "home" ? "active" : ""}`}
              onClick={() => navigate("home")}
            >
              <Home size={18} />
              <span>Home</span>
            </button>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "discover" ? "active" : ""}`}
              onClick={() => navigate("discover")}
            >
              <Compass size={18} />
              <span>Explore</span>
            </button>
            <button
              type="button"
              className={`mobile-nav-item ${currentRoute === "login" ? "active" : ""}`}
              onClick={() => navigate("login")}
            >
              <User size={18} />
              <span>Sign In</span>
            </button>
          </>
        )}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
}
