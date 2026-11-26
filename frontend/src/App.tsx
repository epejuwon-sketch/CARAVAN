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
import { CopilotPage } from "./pages/CopilotPage";
import {
  HowItWorksPage,
  AboutPage,
  ContactPage,
  LegalPrivacyPage,
} from "./pages/StaticPages";
import {
  PrivacyPolicyPage,
  TermsOfServicePage,
  RefundPolicyPage,
  CookiePolicyPage,
  BusinessOperatorPage,
} from "./pages/LegalPages";
import { CookieConsentBanner } from "./components/ui/CookieConsentBanner";
import {
  LayoutDashboard,
  Compass,
  FolderKanban,
  User,
  ShieldCheck,
  Home,
  Lock,
} from "lucide-react";

import { PortalLayout } from "./components/layout/PortalLayout";
import { CopilotWidget } from "./components/copilot/CopilotWidget";

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

  const renderPage = () => {
    switch (currentRoute) {
      case "home": return <HomePage onNavigate={navigate} />;
      case "admin": return <AdminDashboardPage onNavigate={navigate} />;
      case "how-it-works": return <HowItWorksPage onNavigate={navigate} />;
      case "categories": return <CategoriesPage onNavigate={navigate} />;
      case "pricing": return <PricingPage onNavigate={navigate} />;
      case "about": return <AboutPage onNavigate={navigate} />;
      case "contact": return <ContactPage onNavigate={navigate} />;
      case "privacy":
      case "legal-privacy": return <PrivacyPolicyPage onNavigate={navigate} />;
      case "terms": return <TermsOfServicePage onNavigate={navigate} />;
      case "refund": return <RefundPolicyPage onNavigate={navigate} />;
      case "cookies": return <CookiePolicyPage onNavigate={navigate} />;
      case "operator": return <BusinessOperatorPage onNavigate={navigate} />;
      case "login": return <LoginPage onNavigate={navigate} />;
      case "register": return <RegisterPage onNavigate={navigate} />;
      case "discover": return <MarketplacePage onNavigate={navigate} />;
      case "dashboard": return <DashboardPage onNavigate={navigate} />;
      case "eligibility": return <EligibilityPage onNavigate={navigate} />;
      case "applications": return <ApplicationsPage onNavigate={navigate} />;
      case "saved": return <SavedPage onNavigate={navigate} />;
      case "account": return <AccountPage onNavigate={navigate} />;
      case "billing": return <BillingPage />;
      case "support": return <SupportPage />;
      case "copilot": return <CopilotPage onNavigate={navigate} />;
      default: return <HomePage onNavigate={navigate} />;
    }
  };

  const isPortalRoute = [
    "dashboard",
    "discover",
    "applications",
    "admin",
    "account",
    "eligibility",
    "saved",
    "billing",
    "copilot",
  ].includes(currentRoute);

  if (isPortalRoute) {
    return (
      <PortalLayout currentRoute={currentRoute} onNavigate={navigate}>
        {renderPage()}
        <CookieConsentBanner />
      </PortalLayout>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-primary)" }}>
      <Navbar currentRoute={currentRoute} onNavigate={navigate} />
      <main style={{ flex: 1 }}>{renderPage()}</main>
      <Footer onNavigate={navigate} />
      <CookieConsentBanner />
      <CopilotWidget onNavigate={navigate} />
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
