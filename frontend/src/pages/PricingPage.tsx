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
        "Weekly email intelligence digests",
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
        "AI-assisted proposal outline drafting",
        "Investor & grantmaker provenance data",
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
      desc: "For mature ventures managing multimillion-dollar funding operations.",
      features: [
        "All Scaling Venture features",
        "Unlimited application pipelines",
        "Multi-organization portfolio management",
        "Concessionary debt & DFI facility tracking",
        "Dedicated onboarding specialist",
        "Direct Slack / WhatsApp support bridge",
      ],
      cta: "Select Pro",
      highlight: false,
    },
    {
      id: "INSTITUTIONAL",
      name: "Venture Studio & Fund",
      price_usd: "$249",
      price_ngn: "₦380,000",
      period: "per month",
      desc: "For venture builders, incubators, and studios scaling multiple portfolio ventures.",
      features: [
        "All Institutional Scale features",
        "Unlimited portfolio company workspaces",
        "Custom intake & grant syndication feeds",
        "Automated LP & grantmaker compliance reporting",
        "API access for dealflow integration",
        "Dedicated relationship director",
      ],
      cta: "Select Institutional",
      highlight: false,
    },
    {
      id: "CUSTOM",
      name: "Sovereign & DFI Enterprise",
      price_usd: "Custom",
      price_ngn: "Custom",
      period: "annual engagement",
      desc: "For governments, DFIs, and multinational philanthropic programs.",
      features: [
        "Bespoke national or regional funding directories",
        "Sovereign data residency & on-premise deployment",
        "Multi-stakeholder review committee portals",
        "SLA guarantee & custom audit logging",
      ],
      cta: "Contact Enterprise",
      highlight: false,
    },
  ];

  return (
    <div className="container" style={{ paddingTop: 40, display: "flex", flexDirection: "column", gap: 40 }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
        <h1 style={{ fontSize: 36, fontWeight: 800 }}>Predictable, Transparent Pricing</h1>
        <p className="muted" style={{ fontSize: 15, maxWidth: 640 }}>
          Accelerate your funding search with institutional precision. Cancel or switch plans anytime.
        </p>
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button
            type="button"
            className={`btn btn-sm ${currency === "USD" ? "" : "btn-secondary"}`}
            onClick={() => setCurrency("USD")}
          >
            USD ($)
          </button>
          <button
            type="button"
            className={`btn btn-sm ${currency === "NGN" ? "" : "btn-secondary"}`}
            onClick={() => setCurrency("NGN")}
          >
            Nigerian Naira (₦)
          </button>
        </div>
      </div>

      <div className="grid-3" style={{ gap: 20 }}>
        {plans.map((p) => (
          <div
            key={p.id}
            className="card"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 16,
              border: p.highlight ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
              backgroundColor: p.highlight ? "rgba(56, 189, 248, 0.03)" : "var(--bg-card)",
              position: "relative",
            }}
          >
            {p.highlight && (
              <span className="pill pill-cyan" style={{ position: "absolute", top: -10, right: 20 }}>
                Most Popular
              </span>
            )}
            <div>
              <strong style={{ fontSize: 18 }}>{p.name}</strong>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{p.desc}</div>
            </div>

            <div className="row" style={{ gap: 6, alignItems: "baseline" }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)" }}>
                {currency === "USD" ? p.price_usd : p.price_ngn}
              </span>
              <span className="muted" style={{ fontSize: 12 }}>/ {p.period}</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              {p.features.map((f, i) => (
                <div key={i} className="row" style={{ gap: 8, fontSize: 12 }}>
                  <CheckCircle2 size={14} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <button
              type="button"
              className={`btn ${p.highlight ? "" : "btn-secondary"}`}
              style={{ width: "100%", marginTop: 8 }}
              onClick={() => onNavigate("register")}
            >
              {p.cta} <ArrowRight size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
