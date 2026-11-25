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
        {currentRoute === "dashboard" && <DashboardPage onNavigate={navigate} />}
        {currentRoute === "admin" && <AdminDashboardPage onNavigate={navigate} />}
        {currentRoute === "how-it-works" && <HowItWorksPage onNavigate={navigate} />}
        {currentRoute === "categories" && <CategoriesPage onNavigate={navigate} />}
        {currentRoute === "pricing" && <PricingPage onNavigate={navigate} />}
        {currentRoute === "about" && <AboutPage onNavigate={navigate} />}
        {currentRoute === "contact" && <ContactPage onNavigate={navigate} />}
        {currentRoute === "legal-privacy" && <LegalPrivacyPage onNavigate={navigate} />}
        {currentRoute === "login" && <LoginPage onNavigate={navigate} />}
        {currentRoute === "register" && <RegisterPage onNavigate={navigate} />}
        {currentRoute === "discover" && <MarketplacePage onNavigate={navigate} />}
        {currentRoute === "eligibility" && <EligibilityPage onNavigate={navigate} />}
        {currentRoute === "applications" && <ApplicationsPage onNavigate={navigate} />}
        {currentRoute === "saved" && <SavedPage onNavigate={navigate} />}
        {currentRoute === "account" && <AccountPage onNavigate={navigate} />}
        {currentRoute === "billing" && <BillingPage />}
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
