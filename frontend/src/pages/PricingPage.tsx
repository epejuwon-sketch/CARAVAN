import React, { useState } from "react";
import { CheckCircle2, ArrowRight } from "lucide-react";

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
      desc: "For aspiring founders conducting preliminary market and funding discovery.",
      features: [
        "Open verified funding directory",
        "3 eligibility evaluations / month",
        "1 active application workspace",
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
      desc: "For active startups seeking non-dilutive grants and early seed capital.",
      features: [
        "Full verified African & UK catalog",
        "Unlimited eligibility match scoring",
        "5 active application pipelines",
        "Document checklist tracking",
        "Deadline countdown alerts",
        "Standard support queue",
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
      desc: "For scaling ventures optimizing their capital stack across debt and equity.",
      features: [
        "All Emerging Founder features",
        "15 active application pipelines",
        "Proposal outline drafting support",
        "Investor & grantmaker provenance data",
        "Team workspace (up to 3 seats)",
        "Priority support response",
      ],
      cta: "Select Growth",
      highlight: true,
    },
    {
      id: "INSTITUTIONAL",
      name: "Institutional Syndicate",
      price_usd: "$149",
      price_ngn: "₦225,000",
      period: "per month",
      desc: "For incubators, accelerators, universities, and multi-venture studio portfolios.",
      features: [
        "Unlimited application pipelines",
        "Full multi-venture portfolio dashboard",
        "Dedicated account manager",
        "Custom API data access",
        "Bespoke intelligence briefings",
        "10 collaborator seats",
      ],
      cta: "Contact Institutional",
      highlight: false,
    },
  ];

  return (
    <div className="container" style={{ paddingTop: 40, display: "flex", flexDirection: "column", gap: 36 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12 }}>
        <span className="pill pill-gold" style={{ alignSelf: "center" }}>Transparent Pricing</span>
        <h1 style={{ fontSize: 34, fontWeight: 800, color: "#FFFFFF" }}>
          Predictable Capital Intelligence Tiers
        </h1>
        <p className="muted" style={{ fontSize: 14, maxWidth: 580, margin: "0 auto", lineHeight: 1.6 }}>
          Zero commissions on awarded grants or investments. Fixed, predictable monthly subscriptions for African ventures and global scale.
        </p>

        {/* Currency Switcher */}
        <div className="row" style={{ alignSelf: "center", gap: 6, backgroundColor: "var(--bg-secondary)", padding: 4, borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
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

      <div className="grid-4" style={{ gap: 16 }}>
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
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="row-between">
                <strong style={{ fontSize: 16, color: "#FFFFFF" }}>{p.name}</strong>
                {p.highlight && <span className="pill pill-gold">Popular</span>}
              </div>

              <div className="mono gold-text" style={{ fontSize: 28, fontWeight: 800 }}>
                {currency === "USD" ? p.price_usd : p.price_ngn}
                <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 4 }}>/{p.period}</span>
              </div>

              <p className="muted" style={{ fontSize: 12, lineHeight: 1.5 }}>{p.desc}</p>

              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
                <ul style={{ paddingLeft: 0, listStyle: "none", fontSize: 12, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
                  {p.features.map((f, i) => (
                    <li key={i} className="row" style={{ gap: 8 }}>
                      <CheckCircle2 size={13} color="var(--accent-gold-bright)" style={{ flexShrink: 0 }} />
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
              onClick={() => onNavigate("register")}
            >
              {p.cta} <ArrowRight size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
