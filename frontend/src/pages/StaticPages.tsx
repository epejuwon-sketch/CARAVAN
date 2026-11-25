import React from "react";
import { ShieldCheck, Search, Sparkles, FolderKanban, CheckCircle2, ArrowRight, Lock, Globe } from "lucide-react";

export const HowItWorksPage: React.FC<{ onNavigate: (route: string) => void }> = ({ onNavigate }) => {
  const steps = [
    {
      num: "01",
      title: "Automated Provenance Discovery",
      desc: "CARAVAN indexes direct grantmaker registries, DFI programs, and commercial facilities with strict provenance hashing and verified statutory application portals.",
      icon: Search,
    },
    {
      num: "02",
      title: "Algorithmic Eligibility Match Scoring",
      desc: "Our matching engine evaluates your corporate CAC status, jurisdiction, sector, and operating metrics against each program's exact criteria to generate confidence scores.",
      icon: Sparkles,
    },
    {
      num: "03",
      title: "Governed Application Workspaces",
      desc: "Prepare compliant proposals with structured requirements checklists, supporting pitch decks, audited financials, and automatic deadline countdown alerts.",
      icon: FolderKanban,
    },
    {
      num: "04",
      title: "Institutional Capital Closing",
      desc: "Submit through official verified portals. Track pipeline statuses from drafting to formal disbursement with immutable audit logs.",
      icon: CheckCircle2,
    },
  ];

  return (
    <div className="container" style={{ paddingTop: 40, display: "flex", flexDirection: "column", gap: 36 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10 }}>
        <span className="pill pill-gold" style={{ alignSelf: "center" }}>Institutional Lifecycle</span>
        <h1 style={{ fontSize: 34, fontWeight: 800, color: "#FFFFFF" }}>How CARAVAN Works</h1>
        <p className="muted" style={{ fontSize: 14, maxWidth: 640, margin: "0 auto", lineHeight: 1.6 }}>
          A four-stage governed capital intelligence lifecycle built for founders, enterprises, and institutional scale.
        </p>
      </div>

      <div className="grid-2" style={{ gap: 20 }}>
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.num}
              className="card"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 14,
                backgroundColor: "var(--bg-card)",
              }}
            >
              <div className="row-between">
                <span className="mono gold-text" style={{ fontSize: 28, fontWeight: 800 }}>
                  {s.num}
                </span>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-gold)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--accent-gold-bright)",
                  }}
                >
                  <Icon size={18} />
                </div>
              </div>
              <strong style={{ fontSize: 16, color: "#FFFFFF" }}>{s.title}</strong>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>{s.desc}</p>
            </div>
          );
        })}
      </div>

      <div style={{ textAlign: "center", marginTop: 10 }}>
        <button
          type="button"
          className="btn btn-lg"
          onClick={() => onNavigate("register")}
        >
          Get Started with CARAVAN <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
};

export const AboutPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 840, display: "flex", flexDirection: "column", gap: 24 }}>
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="pill pill-gold" style={{ alignSelf: "flex-start" }}>Corporate Governance</span>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>About CARAVAN</h1>
    </div>

    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
      <p>
        <strong>CARAVAN</strong> is an independent institutional funding intelligence, opportunity matching, and application operations platform engineered to power the next generation of African high-growth enterprises and international scale.
      </p>
      <p>
        Headquartered in Abuja, Nigeria with expansion operations in London, UK, CARAVAN addresses the critical information asymmetry and governance barriers that prevent high-conviction African ventures from accessing global institutional funding.
      </p>
      <p>
        Our operating philosophy is grounded in <strong>Zero Fabricated Intelligence</strong>: every grant, debt facility, venture fund, and award on CARAVAN is cryptographically verified against official statutory registry sources.
      </p>
      <div className="row" style={{ gap: 16, marginTop: 10, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
        <span className="pill pill-gold">Zero Fabricated Records</span>
        <span className="pill pill-emerald">100% Cryptographic Provenance</span>
      </div>
    </div>
  </div>
);

export const ContactPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 680, display: "flex", flexDirection: "column", gap: 24 }}>
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="pill pill-gold" style={{ alignSelf: "flex-start" }}>Global Presence</span>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>Institutional Inquiries</h1>
    </div>
    <p className="muted" style={{ fontSize: 14 }}>
      Connect with the CARAVAN partnership director for sovereign directories, DFI facilities, or institutional platform licensing.
    </p>
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 13, backgroundColor: "var(--bg-card)" }}>
      <div className="row-between">
        <span className="muted">Abuja Operations Hub:</span>
        <strong style={{ color: "#FFFFFF" }}>Central Business District, FCT Abuja, Nigeria</strong>
      </div>
      <div className="row-between">
        <span className="muted">London Operations Hub:</span>
        <strong style={{ color: "#FFFFFF" }}>Mayfair / City of London, United Kingdom</strong>
      </div>
      <div className="row-between">
        <span className="muted">Direct Inquiries:</span>
        <span className="mono gold-text font-bold">institutions@caravan.ng</span>
      </div>
      <div className="row-between">
        <span className="muted">Technical Support:</span>
        <span className="mono gold-text font-bold">support@caravan.ng</span>
      </div>
    </div>
  </div>
);

export const LegalPrivacyPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 840, display: "flex", flexDirection: "column", gap: 24 }}>
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="pill pill-gold" style={{ alignSelf: "flex-start" }}>Regulatory Compliance</span>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>Privacy &amp; Data Protection Policy</h1>
    </div>
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
      <p>
        CARAVAN operates under strict compliance with the <strong>Nigeria Data Protection Act (NDPA 2023)</strong> and the <strong>General Data Protection Regulation (GDPR)</strong>.
      </p>
      <p>
        Corporate registration documents, financial statements, and pitch decks uploaded to CARAVAN are encrypted in transit via TLS 1.3 and at rest with AES-256 encryption. We never sell or license proprietary venture data to third parties.
      </p>
      <div className="row" style={{ gap: 14, marginTop: 10, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
        <span className="row muted" style={{ gap: 6, fontSize: 12 }}><Lock size={13} color="var(--accent-gold-bright)" /> End-to-End Encryption</span>
        <span className="row muted" style={{ gap: 6, fontSize: 12 }}><Globe size={13} color="var(--accent-gold-bright)" /> NDPA &amp; GDPR Compliant</span>
      </div>
    </div>
  </div>
);
