import React, { useState } from "react";
import { CheckCircle2, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";

interface PricingPageProps {
  onNavigate: (route: string) => void;
}

export const PricingPage: React.FC<PricingPageProps> = ({ onNavigate }) => {
  const [currency, setCurrency] = useState<"USD" | "NGN">("USD");

  const plans = [
    {
      id: "FREE",
      name: "Community Explorer",
      price_usd: "$0",
      price_ngn: "₦0",
      period: "forever",
      desc: "For aspiring entrepreneurs conducting preliminary funding discovery and initial readiness checks.",
      features: [
        "Open verified funding directory",
        "3 eligibility evaluations / month",
        "1 active application workspace",
        "5 saved opportunities bookmark limit",
        "20 CARAVAN Copilot prompt credits / month",
        "Weekly intelligence digests",
      ],
      cta: "Start Free",
      highlight: false,
    },
    {
      id: "STARTER",
      name: "Emerging Founder",
      price_usd: "$19",
      price_ngn: "₦29,000",
      period: "per month",
      desc: "For active startups seeking non-dilutive grants and early seed capital across Nigeria and Africa.",
      features: [
        "Full verified African & UK catalog",
        "Unlimited eligibility match scoring",
        "3 active application pipelines",
        "25 saved opportunities bookmark limit",
        "100 CARAVAN Copilot prompt credits / month",
        "Export readiness & eligibility reports",
        "Document checklist tracking",
      ],
      cta: "Select Starter",
      highlight: false,
    },
    {
      id: "GROWTH",
      name: "Scaling Venture",
      price_usd: "$49",
      price_ngn: "₦75,000",
      period: "per month",
      desc: "For scaling ventures optimizing their capital stack across grants, concessionary loans and equity.",
      features: [
        "All Emerging Founder features",
        "15 active application pipelines",
        "100 saved opportunities bookmark limit",
        "500 CARAVAN Copilot prompt credits / month",
        "AI proposal outline drafting assistance",
        "Team workspace (up to 3 collaborator seats)",
        "Priority support response",
      ],
      cta: "Select Growth",
      highlight: true,
    },
    {
      id: "PRO",
      name: "Institutional Scale",
      price_usd: "$99",
      price_ngn: "₦150,000",
      period: "per month",
      desc: "For established businesses targeting DFI facilities, commercial debts, and regional expansion.",
      features: [
        "All Scaling Venture features",
        "50 active application pipelines",
        "500 saved opportunities bookmark limit",
        "2,000 CARAVAN Copilot prompt credits / month",
        "Concessionary debt & DFI facility tracking",
        "Multi-organization portfolio management",
        "5 collaborator seats & dedicated onboarding",
      ],
      cta: "Select Pro",
      highlight: false,
    },
    {
      id: "BUSINESS",
      name: "Venture Studio & Fund",
      price_usd: "$249",
      price_ngn: "₦380,000",
      period: "per month",
      desc: "For incubators, accelerators, venture studios, and funds managing multi-company dealflow.",
      features: [
        "All Institutional Scale features",
        "Unlimited application pipelines",
        "Unlimited saved opportunities",
        "10,000 CARAVAN Copilot prompt credits / month",
        "Unlimited portfolio company workspaces",
        "Team workspace (up to 25 collaborator seats)",
        "API access for private dealflow integration",
      ],
      cta: "Select Business",
      highlight: false,
    },
    {
      id: "ENTERPRISE",
      name: "Sovereign & DFI Enterprise",
      price_usd: "Custom",
      price_ngn: "Custom",
      period: "bespoke agreement",
      desc: "For sovereign development funds, multilateral agencies, and national ministry programs.",
      features: [
        "Bespoke national or regional funding directories",
        "Sovereign data residency & on-premise deployments",
        "Unlimited Copilot credits & fine-tuned models",
        "Multi-stakeholder review committees",
        "SLA guarantee & custom audit logging",
        "Dedicated relationship director",
      ],
      cta: "Contact Enterprise",
      highlight: false,
    },
  ];

  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, display: "flex", flexDirection: "column", gap: 36 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12 }}>
        <span className="pill pill-gold" style={{ alignSelf: "center" }}>Transparent Institutional Pricing</span>
        <h1 style={{ fontSize: 34, fontWeight: 800, color: "#FFFFFF" }}>
          Predictable Capital Intelligence Tiers
        </h1>
        <p className="muted" style={{ fontSize: 14, maxWidth: 620, margin: "0 auto", lineHeight: 1.6 }}>
          Zero commissions on awarded grants or investments. Fixed, predictable monthly subscriptions for Nigerian ventures, African scale-ups, and institutional syndicates.
        </p>

        {/* Currency Switcher */}
        <div className="row" style={{ alignSelf: "center", gap: 6, backgroundColor: "var(--bg-secondary)", padding: 4, borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", marginTop: 8 }}>
          <button
            type="button"
            className={`btn btn-sm ${currency === "USD" ? "btn" : "btn-secondary"}`}
            onClick={() => setCurrency("USD")}
          >
            USD ($)
          </button>
          <button
            type="button"
            className={`btn btn-sm ${currency === "NGN" ? "btn" : "btn-secondary"}`}
            onClick={() => setCurrency("NGN")}
          >
            NGN (₦)
          </button>
        </div>
      </div>

      {/* 6 Plans Grid */}
      <div className="grid-3" style={{ gap: 20 }}>
        {plans.map((p) => (
          <div
            key={p.id}
            className={`card ${p.highlight ? "card-gold" : ""}`}
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              gap: 20,
              padding: "28px 24px",
              backgroundColor: "var(--bg-card)",
              position: "relative",
              border: p.highlight ? "1.5px solid #C69D49" : "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="row-between">
                <strong style={{ fontSize: 17, color: "#FFFFFF" }}>{p.name}</strong>
                {p.highlight && <span className="pill pill-gold">Most Popular</span>}
              </div>

              <div className="mono gold-text" style={{ fontSize: 28, fontWeight: 800 }}>
                {currency === "USD" ? p.price_usd : p.price_ngn}
                <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 6 }}>/{p.period}</span>
              </div>

              <p className="muted" style={{ fontSize: 12, lineHeight: 1.5 }}>{p.desc}</p>

              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
                <ul style={{ paddingLeft: 0, listStyle: "none", fontSize: 12, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
                  {p.features.map((f, i) => (
                    <li key={i} className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                      <CheckCircle2 size={14} color="var(--accent-gold-bright)" style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <button
              type="button"
              className={p.highlight ? "btn" : "btn btn-secondary"}
              style={{ width: "100%", justifyContent: "center" }}
              onClick={() => onNavigate("billing")}
            >
              {p.cta} <ArrowRight size={13} />
            </button>
          </div>
        ))}
      </div>

      {/* Feature Comparison Table */}
      <div className="card" style={{ padding: "32px 28px", backgroundColor: "var(--bg-secondary)", marginTop: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#FFFFFF", marginBottom: 16 }}>
          Comprehensive Tier Capability Comparison
        </h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                <th style={{ padding: "12px 10px" }}>Capability</th>
                <th style={{ padding: "12px 10px" }}>Free</th>
                <th style={{ padding: "12px 10px" }}>Starter ($19)</th>
                <th style={{ padding: "12px 10px" }}>Growth ($49)</th>
                <th style={{ padding: "12px 10px" }}>Pro ($99)</th>
                <th style={{ padding: "12px 10px" }}>Business ($249)</th>
                <th style={{ padding: "12px 10px" }}>Enterprise</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>Copilot Prompt Credits</td>
                <td style={{ padding: "10px" }}>20 / mo</td>
                <td style={{ padding: "10px" }}>100 / mo</td>
                <td style={{ padding: "10px" }}>500 / mo</td>
                <td style={{ padding: "10px" }}>2,000 / mo</td>
                <td style={{ padding: "10px" }}>10,000 / mo</td>
                <td style={{ padding: "10px" }}>Unlimited / Custom</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>Active Application Workspaces</td>
                <td style={{ padding: "10px" }}>1</td>
                <td style={{ padding: "10px" }}>3</td>
                <td style={{ padding: "10px" }}>15</td>
                <td style={{ padding: "10px" }}>50</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>Saved Opportunity Bookmarks</td>
                <td style={{ padding: "10px" }}>5</td>
                <td style={{ padding: "10px" }}>25</td>
                <td style={{ padding: "10px" }}>100</td>
                <td style={{ padding: "10px" }}>500</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>Document Storage / Pipeline</td>
                <td style={{ padding: "10px" }}>3 docs</td>
                <td style={{ padding: "10px" }}>10 docs</td>
                <td style={{ padding: "10px" }}>25 docs</td>
                <td style={{ padding: "10px" }}>100 docs</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
                <td style={{ padding: "10px" }}>Unlimited</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>Team Seats</td>
                <td style={{ padding: "10px" }}>1 user</td>
                <td style={{ padding: "10px" }}>1 user</td>
                <td style={{ padding: "10px" }}>3 users</td>
                <td style={{ padding: "10px" }}>5 users</td>
                <td style={{ padding: "10px" }}>25 users</td>
                <td style={{ padding: "10px" }}>Bespoke</td>
              </tr>
              <tr>
                <td style={{ padding: "10px", fontWeight: 600 }}>AI Proposal Outlining</td>
                <td style={{ padding: "10px" }}>—</td>
                <td style={{ padding: "10px" }}>—</td>
                <td style={{ padding: "10px" }}>Included</td>
                <td style={{ padding: "10px" }}>Included</td>
                <td style={{ padding: "10px" }}>Included</td>
                <td style={{ padding: "10px" }}>Fine-Tuned Model</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
