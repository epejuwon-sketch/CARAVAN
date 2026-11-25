import React from "react";
import { ShieldCheck, Search, Sparkles, FolderKanban, CheckCircle2, ArrowRight } from "lucide-react";

export const HowItWorksPage: React.FC<{ onNavigate: (route: string) => void }> = ({ onNavigate }) => {
  const steps = [
    {
      num: "01",
      title: "Automated Provenance Discovery",
      desc: "CARAVAN indexes direct grantmaker registries, DFI programs, and commercial facilities with strict provenance hashing and verified application portals.",
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
    <div className="container" style={{ paddingTop: 40, display: "flex", flexDirection: "column", gap: 40 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ fontSize: 36, fontWeight: 800 }}>How CARAVAN Works</h1>
        <p className="muted" style={{ fontSize: 15, maxWidth: 640, margin: "0 auto" }}>
          A four-stage governed capital intelligence lifecycle built for founders and institutional scale.
        </p>
      </div>

      <div className="grid-2" style={{ gap: 24 }}>
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.num} className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="row-between">
                <span className="mono" style={{ fontSize: 28, fontWeight: 800, color: "var(--accent-cyan)" }}>{s.num}</span>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: "rgba(56, 189, 248, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-cyan)" }}>
                  <Icon size={18} />
                </div>
              </div>
              <strong style={{ fontSize: 18 }}>{s.title}</strong>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>{s.desc}</p>
            </div>
          );
        })}
      </div>

      <div style={{ textAlign: "center", marginTop: 20 }}>
        <button type="button" className="btn" style={{ padding: "12px 28px" }} onClick={() => onNavigate("register")}>
          Get Started with CARAVAN <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
};

export const AboutPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 800, display: "flex", flexDirection: "column", gap: 24 }}>
    <h1 style={{ fontSize: 32, fontWeight: 800 }}>About CARAVAN</h1>
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16, lineHeight: 1.7, fontSize: 14 }}>
      <p>
        <strong>CARAVAN</strong> is an independent institutional funding intelligence, opportunity matching, and application operations platform engineered to power the next generation of African high-growth enterprises and international scale.
      </p>
      <p>
        Headquartered in Abuja, Nigeria with expansion operations in London, UK, CARAVAN addresses the critical information asymmetry and governance barriers that prevent high-conviction African ventures from accessing global institutional funding.
      </p>
      <p>
        Our operating philosophy is grounded in <strong>Zero Fabricated Intelligence</strong>: every grant, debt facility, venture fund, and award on CARAVAN is cryptographically verified against official registry sources.
      </p>
    </div>
  </div>
);

export const ContactPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 640, display: "flex", flexDirection: "column", gap: 24 }}>
    <h1 style={{ fontSize: 32, fontWeight: 800 }}>Institutional Inquiries</h1>
    <p className="muted" style={{ fontSize: 14 }}>
      Connect with the CARAVAN partnership director for sovereign directories, DFI facilities, or venture studio licensing.
    </p>
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14, fontSize: 13 }}>
      <div className="row-between">
        <span className="muted">Abuja Operations Hub:</span>
        <strong>Central Business District, FCT Abuja, Nigeria</strong>
      </div>
      <div className="row-between">
        <span className="muted">London Operations Hub:</span>
        <strong>Mayfair / City of London, United Kingdom</strong>
      </div>
      <div className="row-between">
        <span className="muted">Official Inquiries:</span>
        <strong className="mono" style={{ color: "var(--accent-cyan)" }}>partnerships@caravanfunding.com</strong>
      </div>
    </div>
  </div>
);

export const LegalPrivacyPage: React.FC<{ onNavigate: (route: string) => void }> = () => (
  <div className="container" style={{ paddingTop: 40, maxWidth: 800, display: "flex", flexDirection: "column", gap: 24 }}>
    <h1 style={{ fontSize: 32, fontWeight: 800 }}>Data Protection &amp; Privacy Policy</h1>
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14, lineHeight: 1.6, fontSize: 13 }}>
      <p>
        CARAVAN operates in full compliance with the <strong>Nigeria Data Protection Regulation (NDPR)</strong>, the <strong>Nigeria Data Protection Act 2023</strong>, and the <strong>UK General Data Protection Regulation (UK GDPR)</strong>.
      </p>
      <p>
        <strong>Confidentiality Guarantee:</strong> Pitch decks, financial projections, tax identification records, and cap tables uploaded to CARAVAN remain the exclusive proprietary property of the uploading organization and are never shared or published without explicit authorization.
      </p>
      <p>
        <strong>AEGIS Security Identity:</strong> All customer data is isolated at rest and in transit using AES-256 and TLS 1.3 encryption.
      </p>
    </div>
  </div>
);
