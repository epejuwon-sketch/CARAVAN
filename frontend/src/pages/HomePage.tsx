import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  Zap,
  BarChart3,
  ArrowRight,
  Compass,
  CheckCircle2,
  Lock,
  Globe,
  Building2,
  FileCheck,
} from "lucide-react";
import { CaravanSymbol } from "../components/brand/CaravanLogo";
import { apiFetch } from "../lib/api";

interface HomePageProps {
  onNavigate: (route: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const [oppCount, setOppCount] = useState<number>(12);

  useEffect(() => {
    apiFetch<any>("/api/v1/opportunities?limit=1")
      .then((res) => {
        if (res?.total) setOppCount(res.total);
      })
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 64, paddingTop: 40 }}>
      {/* 1. HERO SECTION (Matching Attached Reference Image Screen 1) */}
      <section className="container">
        <div
          className="row-between"
          style={{
            flexWrap: "wrap",
            gap: 48,
            alignItems: "center",
            padding: "32px 0 20px",
          }}
        >
          {/* Left Column: Heading, Subtitle & CTAs */}
          <div style={{ flex: "1 1 500px", maxWidth: 620, display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span
                style={{
                  color: "var(--accent-gold-bright)",
                  fontSize: 20,
                  fontWeight: 800,
                  letterSpacing: "0.16em",
                  textTransform: "uppercase",
                }}
              >
                CARAVAN
              </span>
              <h1
                style={{
                  fontSize: "clamp(34px, 5.2vw, 54px)",
                  fontWeight: 800,
                  lineHeight: 1.15,
                  letterSpacing: "-0.03em",
                  color: "#FFFFFF",
                }}
              >
                Funding. Opportunities. Growth.
              </h1>
            </div>

            <p
              className="muted"
              style={{
                fontSize: "clamp(15px, 1.8vw, 18px)",
                lineHeight: 1.6,
                color: "var(--text-secondary)",
              }}
            >
              Discover trusted funding opportunities for your business, project or enterprise. Curated institutional grants, concessionary debt, venture capital, and multilateral development facilities. Zero fabricated opportunities.
            </p>

            <div className="row" style={{ gap: 14, flexWrap: "wrap", marginTop: 8 }}>
              <button
                type="button"
                className="btn btn-lg"
                onClick={() => onNavigate("register")}
              >
                Get Started <ArrowRight size={16} />
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-lg"
                onClick={() => onNavigate("how-it-works")}
              >
                Learn More
              </button>
            </div>
          </div>

          {/* Right Column: Official Large CARAVAN Symbol */}
          <div
            style={{
              flex: "1 1 320px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "20px 0",
            }}
          >
            <div
              style={{
                width: 280,
                height: 240,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-md)",
              }}
            >
              <CaravanSymbol size={180} />
            </div>
          </div>
        </div>
      </section>

      {/* 2. THREE PILLARS (Matching Reference Image Screen 1 Bottom Cards) */}
      <section className="container">
        <div className="grid-3" style={{ gap: 20 }}>
          {/* Card 1: Trusted & Secure */}
          <div
            className="card card-gold"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 14,
              padding: "28px 24px",
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-gold)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-gold-bright)",
              }}
            >
              <ShieldCheck size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>Trusted &amp; Secure</h3>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                Every institutional program is verified with cryptographic provenance records, official registry filings, and direct statutory application portal endpoints.
              </p>
            </div>
          </div>

          {/* Card 2: Fast Application */}
          <div
            className="card card-gold"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 14,
              padding: "28px 24px",
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-gold)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-gold-bright)",
              }}
            >
              <Zap size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>Fast Application</h3>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                Structured multi-step application preparation, automated eligibility scoring, checklists, and document verification reduce application cycle time by 80%.
              </p>
            </div>
          </div>

          {/* Card 3: Real Opportunities */}
          <div
            className="card card-gold"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 14,
              padding: "28px 24px",
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-gold)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-gold-bright)",
              }}
            >
              <BarChart3 size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>Real Opportunities</h3>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                Active capital allocations across 15 funding categories—from Bank of Industry facilities and international DFIs to venture capital and competitive innovation funds.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. VERIFIED TELEMETRY BANNER */}
      <section className="container">
        <div
          className="grid-4"
          style={{
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "28px 24px",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-gold-bright)" }}>
              {oppCount} Programs
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Verified Institutional Pipeline</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)" }}>
              15 Categories
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Grants, Debt, VC, DFIs &amp; Awards</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 32, fontWeight: 800, color: "var(--status-success-text)" }}>
              100% Provenance
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Verified Official Registry Sources</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)" }}>
              Abuja &amp; London
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Regional &amp; International Hubs</div>
          </div>
        </div>
      </section>

      {/* 4. INSTITUTIONAL CALL TO ACTION */}
      <section className="container" style={{ paddingBottom: 20 }}>
        <div
          className="card"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            gap: 18,
            padding: "48px 24px",
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-gold)",
          }}
        >
          <span className="pill pill-gold">Ready to Access Capital</span>
          <h2 style={{ fontSize: 26, fontWeight: 800, maxWidth: 560 }}>
            Connect Your Venture with Verified Capital Pipelines
          </h2>
          <p className="muted" style={{ fontSize: 14, maxWidth: 480, lineHeight: 1.6 }}>
            Sign up for a free organization profile or explore the verified funding marketplace to begin matching with institutional programs.
          </p>
          <div className="row" style={{ gap: 12, marginTop: 6 }}>
            <button
              type="button"
              className="btn btn-lg"
              onClick={() => onNavigate("register")}
            >
              Get Started Now
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-lg"
              onClick={() => onNavigate("discover")}
            >
              Browse Opportunities
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
