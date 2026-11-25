import React, { useState } from "react";
import { AuthProvider, useAuth } from "./lib/auth";
import { Navbar } from "./components/layout/Navbar";
import { Footer } from "./components/layout/Footer";
import { HomePage } from "./pages/HomePage";
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

function MainContent() {
  const { user, loading } = useAuth();
  const [currentRoute, setCurrentRoute] = useState<string>("home");

  // Handle URL hash or direct route
  const navigate = (route: string) => {
    setCurrentRoute(route);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="muted mono" style={{ fontSize: 13 }}>Initializing CARAVAN Platform...</div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar currentRoute={currentRoute} onNavigate={navigate} />

      <main style={{ flex: 1 }}>
        {currentRoute === "home" && <HomePage onNavigate={navigate} />}
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
