import React from "react";
import { ArrowRight, CheckCircle2, Briefcase } from "lucide-react";

interface CategoriesPageProps {
  onNavigate: (route: string) => void;
}

export const CategoriesPage: React.FC<CategoriesPageProps> = ({ onNavigate }) => {
  const categories = [
    { id: "GRANT", title: "Non-Dilutive Grants", desc: "Direct institutional, sovereign, and philanthropic grants with no equity dilution or repayment requirements.", scope: "Pan-African & Global" },
    { id: "LOAN", title: "Concessionary Debt & Loans", desc: "Low-interest commercial or public development bank loans with single-digit rates and extended moratoriums.", scope: "BOI, DBN & Commercial PFIs" },
    { id: "VENTURE_CAPITAL", title: "Venture Capital", desc: "Institutional Series A, B, and Growth venture funds investing in high-conviction tech and scalable business models.", scope: "Global & African VCs" },
    { id: "ANGEL_INVESTMENT", title: "Angel Investment", desc: "Accredited angel syndicates, high-net-worth angel networks, and early founder backing.", scope: "Syndicate Networks" },
    { id: "SEED_FUNDING", title: "Pre-Seed & Seed Equity", desc: "Early-stage institutional startup equity financing for product validation and initial customer acquisition.", scope: "Accelerators & Micro-VCs" },
    { id: "ACCELERATOR", title: "Accelerators & Incubators", desc: "Cohort-based capital, world-class mentorship, technical credits, and international market access.", scope: "Google, YC, Techstars" },
    { id: "COMPETITION", title: "Competitions & Challenges", desc: "Innovation prize competitions, hackathons, and national business plan challenges with cash awards.", scope: "AfDB, AU & Corporate" },
    { id: "AWARD", title: "Merit Honors & Awards", desc: "Civic, scientific, and industry recognition prizes recognizing leadership, environmental, and tech impact.", scope: "Global Fellowships" },
    { id: "WORKING_CAPITAL", title: "Working Capital Facilities", desc: "Invoice factoring, trade credit facilities, purchase order financing, and cash flow smoothing lines.", scope: "FinTechs & Banks" },
    { id: "EQUIPMENT_FINANCING", title: "Equipment & Asset Financing", desc: "Capex leasing and industrial machinery financing for processing, healthcare, logistics, and data infrastructure.", scope: "Development Finance" },
    { id: "CORPORATE_FUNDING", title: "Corporate Venture & Pilots", desc: "Strategic venture capital arms of multinational corporates, proof-of-concept pilot grants, and commercial partnerships.", scope: "Enterprise Partners" },
    { id: "INSTITUTIONAL_FINANCE", title: "Development & DFI Finance", desc: "Multilateral development financial institutions (IFC, AfDB, BII, FMO) supporting systemic economic infrastructure.", scope: "Sovereign Programs" },
    { id: "RESEARCH_FUNDING", title: "R&D & Science Grants", desc: "Academic and industrial technological research grants funding breakthroughs in AI, bio-sciences, and clean energy.", scope: "UKRI, Gates, Horizon" },
    { id: "PHILANTHROPIC_FUNDING", title: "Philanthropic Foundations", desc: "Endowed private foundations supporting climate resilience, financial inclusion, youth employment, and public health.", scope: "Mastercard, Ford, Rockefeller" },
    { id: "SCHOLARSHIP", title: "Executive Fellowships & Scholarships", desc: "Leadership, technological talent, and doctoral research training fellowships supporting next-gen builders.", scope: "Rhodes, Mandela, Chevening" },
  ];

  return (
    <div className="container" style={{ paddingTop: 40, display: "flex", flexDirection: "column", gap: 36 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10 }}>
        <span className="pill pill-gold" style={{ alignSelf: "center" }}>Comprehensive Institutional Stack</span>
        <h1 style={{ fontSize: 34, fontWeight: 800, color: "#FFFFFF" }}>15 Institutional Funding Categories</h1>
        <p className="muted" style={{ fontSize: 14, maxWidth: 640, margin: "0 auto", lineHeight: 1.6 }}>
          CARAVAN catalogs the entire capital stack from early proof-of-concept grants to multinational development finance facilities.
        </p>
      </div>

      <div className="grid-3" style={{ gap: 16 }}>
        {categories.map((c) => (
          <div
            key={c.id}
            className="card"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12,
              backgroundColor: "var(--bg-card)",
            }}
          >
            <div className="row-between">
              <span className="pill pill-gold">{c.id}</span>
              <span className="muted mono" style={{ fontSize: 11 }}>{c.scope}</span>
            </div>
            <strong style={{ fontSize: 15, color: "#FFFFFF" }}>{c.title}</strong>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6, flex: 1 }}>{c.desc}</p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ marginTop: 6 }}
              onClick={() => onNavigate("discover")}
            >
              Browse Category <ArrowRight size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
