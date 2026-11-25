import React from "react";
import {
  Compass,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Lock,
  Globe,
  Building2,
  TrendingUp,
} from "lucide-react";

interface HomePageProps {
  onNavigate: (route: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 80, paddingTop: 40 }}>
      {/* Hero Section */}
      <section className="container" style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 24 }}>
        <div className="pill pill-cyan">
          <ShieldCheck size={13} /> Official Provenance Verified Funding Intelligence
        </div>
        <h1 style={{
          fontSize: "clamp(36px, 6vw, 64px)",
          fontWeight: 800,
          letterSpacing: "-0.03em",
          lineHeight: 1.1,
          maxWidth: 960,
          background: "linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}>
          Capital Intelligence for High-Growth Ventures &amp; Global Scale
        </h1>
        <p className="muted" style={{ fontSize: "clamp(15px, 2vw, 18px)", maxWidth: 680, lineHeight: 1.6 }}>
          CARAVAN bridges high-conviction African enterprises with global non-dilutive grants, concessionary debt, venture capital, and multilateral development facilities. Zero fabricated opportunities.
        </p>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", justifyContent: "center", marginTop: 12 }}>
          <button type="button" className="btn" style={{ padding: "14px 28px", fontSize: 14 }} onClick={() => onNavigate("register")}>
            Explore Funding Opportunities <ArrowRight size={16} />
          </button>
          <button type="button" className="btn btn-secondary" style={{ padding: "14px 28px", fontSize: 14 }} onClick={() => onNavigate("how-it-works")}>
            How It Works
          </button>
        </div>
      </section>

      {/* Metrics Banner */}
      <section className="container">
        <div className="grid-4" style={{
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "32px 24px",
        }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-cyan)" }}>$6.5M+</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Verified Active Pipeline</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-indigo)" }}>15 Categories</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Grants, Debt, VC, DFIs &amp; Awards</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-emerald)" }}>100% Provenance</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Verified Official Registry Sources</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-amber)" }}>Abuja &amp; London</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Regional &amp; International Hubs</div>
          </div>
        </div>
      </section>

      {/* Value Pillars */}
      <section className="container" style={{ display: "flex", flexDirection: "column", gap: 36 }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 28, fontWeight: 800 }}>Engineered for Institutional Rigor</h2>
          <p className="muted" style={{ fontSize: 14, maxWidth: 540, margin: "0 auto" }}>
            CARAVAN replaces unstructured search with verified intelligence pipelines and governed preparation workflows.
          </p>
        </div>

        <div className="grid-3">
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 8, background: "rgba(56, 189, 248, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-cyan)" }}>
              <Compass size={20} />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>Verified Capital Catalog</h3>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
              Direct programmatic links to official grantmaker, commercial bank, venture fund, and DFI application portals with cryptographic provenance hashes.
            </p>
          </div>

          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 8, background: "rgba(129, 140, 248, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-indigo)" }}>
              <Sparkles size={20} />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>Smart Eligibility Matching</h3>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
              Rule-governed matching based on CAC corporate structure, geography, stage, sector, and revenue. Clear scoring breakdowns ensure zero wasted effort.
            </p>
          </div>

          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 8, background: "rgba(52, 211, 153, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-emerald)" }}>
              <ShieldCheck size={20} />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>Application Workspace</h3>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
              Track drafting progress, organize cap tables and pitch decks, set automatic deadline countdown reminders, and maintain institutional audit logs.
            </p>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="container">
        <div style={{
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border-hover)",
          borderRadius: "var(--radius-lg)",
          padding: "60px 32px",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}>
          <h2 style={{ fontSize: 32, fontWeight: 800 }}>Ready to Accelerate Your Venture Capital Journey?</h2>
          <p className="muted" style={{ fontSize: 14, maxWidth: 560, lineHeight: 1.6 }}>
            Join forward-thinking African founders and institutional leaders securing non-dilutive grants, expansion loans, and equity funding on CARAVAN.
          </p>
          <button type="button" className="btn" style={{ padding: "14px 32px", fontSize: 14 }} onClick={() => onNavigate("register")}>
            Create Free Account <ArrowRight size={16} />
          </button>
        </div>
      </section>
    </div>
  );
};
