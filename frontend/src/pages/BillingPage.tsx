import React, { useEffect, useState } from "react";
import { CreditCard, CheckCircle2, ShieldCheck, ArrowRight, Zap, Lock, Sparkles, FolderKanban, Bookmark, FileText } from "lucide-react";
import { Subscription } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge } from "../components/ui/DesignSystem";

export const BillingPage: React.FC = () => {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<any | null>(null);
  const [tiers, setTiers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [simulating, setSimulating] = useState(false);

  async function loadBilling() {
    setLoading(true);
    try {
      const [cur, allTiers, usageData] = await Promise.all([
        apiFetch<any>("/api/v1/subscriptions/current"),
        apiFetch<any>("/api/v1/subscriptions/tiers"),
        apiFetch<any>("/api/v1/subscriptions/usage"),
      ]);
      setSub(cur);
      setTiers(allTiers.tiers || []);
      setUsage(usageData);
    } catch (err: any) {
      setMsg(err.message || "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBilling();
  }, []);

  async function handleInstantSandboxUpgrade(tier: string) {
    setSimulating(true);
    setMsg("");
    try {
      const res = await apiFetch<any>("/api/v1/subscriptions/sandbox-upgrade", {
        method: "POST",
        body: JSON.stringify({ tier }),
      });
      setMsg(`Upgraded successfully to ${res.tier_name || tier} (Sandbox Mode)`);
      await loadBilling();
    } catch (err: any) {
      setMsg(err.message);
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, paddingBottom: 60, display: "flex", flexDirection: "column", gap: 28, maxWidth: 1040 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
          Subscription &amp; Entitlements
        </h1>
        <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
          Manage your organization tier, statutory application capacities, and payment gateway rails.
        </p>
      </div>

      {msg && (
        <div className="pill pill-gold" style={{ padding: "10px 16px", fontSize: 13, alignSelf: "flex-start" }}>
          {msg}
        </div>
      )}

      {/* Active Subscription Status Banner */}
      {sub && (
        <div
          className="card card-gold"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
            padding: "24px 28px",
            backgroundColor: "var(--bg-secondary)",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="muted" style={{ fontSize: 12 }}>Current Subscription</span>
            <div className="row" style={{ gap: 10 }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: "#FFFFFF" }}>{sub.tier_name}</span>
              <StatusBadge status={sub.status} />
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Plan Price: <span className="gold-text mono">${sub.price_usd}/mo</span> · Renewal:{" "}
              {sub.renewal_date ? new Date(sub.renewal_date).toLocaleDateString() : "Active Entitlement"}
            </div>
          </div>

          <div className="row" style={{ gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
            <span className="row" style={{ gap: 6, backgroundColor: "rgba(198, 157, 73, 0.1)", padding: "6px 12px", borderRadius: "var(--radius-sm)", border: "1px solid rgba(198, 157, 73, 0.2)" }}>
              <Lock size={13} color="var(--accent-gold-bright)" /> Sandbox Billing Mode Active
            </span>
          </div>
        </div>
      )}

      {/* Live Quota Usage Meters */}
      {usage && usage.quotas && (
        <div className="card" style={{ padding: "24px 28px", backgroundColor: "var(--bg-card)", display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="row-between">
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#FFFFFF" }}>
              Monthly Capacity &amp; Resource Usage
            </h2>
            <span className="mono muted" style={{ fontSize: 12 }}>
              Cycle: {usage.billing_cycle}
            </span>
          </div>

          <div className="grid-4" style={{ gap: 16 }}>
            {/* Copilot Credits */}
            <div style={{ backgroundColor: "var(--bg-secondary)", padding: "16px 18px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="row-between">
                <span className="row" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <Sparkles size={14} color="var(--accent-gold-bright)" /> Copilot Credits
                </span>
                <span className="mono gold-text" style={{ fontSize: 13, fontWeight: 700 }}>
                  {usage.quotas.copilot_credits.used} / {usage.quotas.copilot_credits.limit}
                </span>
              </div>
              <div style={{ width: "100%", height: 6, backgroundColor: "#222222", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(100, (usage.quotas.copilot_credits.used / usage.quotas.copilot_credits.limit) * 100)}%`,
                    backgroundColor: "#C69D49",
                  }}
                />
              </div>
              <span className="muted" style={{ fontSize: 11 }}>
                {usage.quotas.copilot_credits.remaining} prompt credits remaining
              </span>
            </div>

            {/* Active Applications */}
            <div style={{ backgroundColor: "var(--bg-secondary)", padding: "16px 18px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="row-between">
                <span className="row" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <FolderKanban size={14} color="#60A5FA" /> Application Pipelines
                </span>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: "#FFFFFF" }}>
                  {usage.quotas.active_applications.used} / {usage.quotas.active_applications.unlimited ? "∞" : usage.quotas.active_applications.limit}
                </span>
              </div>
              <div style={{ width: "100%", height: 6, backgroundColor: "#222222", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: usage.quotas.active_applications.unlimited
                      ? "10%"
                      : `${Math.min(100, (usage.quotas.active_applications.used / usage.quotas.active_applications.limit) * 100)}%`,
                    backgroundColor: "#60A5FA",
                  }}
                />
              </div>
              <span className="muted" style={{ fontSize: 11 }}>
                {usage.quotas.active_applications.unlimited ? "Unlimited pipelines" : `${usage.quotas.active_applications.remaining} available`}
              </span>
            </div>

            {/* Saved Opportunities */}
            <div style={{ backgroundColor: "var(--bg-secondary)", padding: "16px 18px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="row-between">
                <span className="row" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <Bookmark size={14} color="#34D399" /> Bookmarks
                </span>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: "#FFFFFF" }}>
                  {usage.quotas.saved_opportunities.used} / {usage.quotas.saved_opportunities.unlimited ? "∞" : usage.quotas.saved_opportunities.limit}
                </span>
              </div>
              <div style={{ width: "100%", height: 6, backgroundColor: "#222222", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: usage.quotas.saved_opportunities.unlimited
                      ? "10%"
                      : `${Math.min(100, (usage.quotas.saved_opportunities.used / usage.quotas.saved_opportunities.limit) * 100)}%`,
                    backgroundColor: "#34D399",
                  }}
                />
              </div>
              <span className="muted" style={{ fontSize: 11 }}>
                {usage.quotas.saved_opportunities.unlimited ? "Unlimited bookmarks" : `${usage.quotas.saved_opportunities.remaining} slots remaining`}
              </span>
            </div>

            {/* Documents */}
            <div style={{ backgroundColor: "var(--bg-secondary)", padding: "16px 18px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="row-between">
                <span className="row" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <FileText size={14} color="#F472B6" /> Documents Vault
                </span>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: "#FFFFFF" }}>
                  {usage.quotas.documents_per_app.total_documents} docs
                </span>
              </div>
              <div style={{ width: "100%", height: 6, backgroundColor: "#222222", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: "25%", backgroundColor: "#F472B6" }} />
              </div>
              <span className="muted" style={{ fontSize: 11 }}>
                Max {usage.quotas.documents_per_app.unlimited ? "Unlimited" : usage.quotas.documents_per_app.limit} docs / workspace
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tiers Grid */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#FFFFFF" }}>Available Tier Entitlements</h2>

        <div className="grid-3" style={{ gap: 16 }}>
          {tiers.slice(0, 6).map((t) => {
            const isCurrent = sub?.tier === t.tier;
            return (
              <div
                key={t.tier}
                className={`card ${isCurrent ? "card-gold" : ""}`}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: 16,
                  padding: "24px 20px",
                  backgroundColor: "var(--bg-card)",
                  border: isCurrent ? "1.5px solid #C69D49" : "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div className="row-between">
                    <strong style={{ fontSize: 16, color: "#FFFFFF" }}>{t.name}</strong>
                    {isCurrent && <span className="pill pill-gold">Active</span>}
                  </div>

                  <div className="mono gold-text" style={{ fontSize: 24, fontWeight: 800 }}>
                    {t.price_usd === 0 ? "Free" : `$${t.price_usd}`}{" "}
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>/mo</span>
                  </div>

                  <ul style={{ paddingLeft: 18, fontSize: 12, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 6 }}>
                    {(t.features || []).map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>

                {!isCurrent && (
                  <button
                    type="button"
                    className="btn btn-sm"
                    style={{ width: "100%", justifyContent: "center" }}
                    disabled={simulating}
                    onClick={() => handleInstantSandboxUpgrade(t.tier)}
                  >
                    Activate {t.name} (Sandbox)
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
