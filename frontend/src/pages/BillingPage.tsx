import React, { useEffect, useState } from "react";
import { CreditCard, CheckCircle2, ShieldCheck, ArrowRight, Zap, Lock } from "lucide-react";
import { Subscription } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge } from "../components/ui/DesignSystem";

export const BillingPage: React.FC = () => {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [tiers, setTiers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [simulating, setSimulating] = useState(false);

  async function loadBilling() {
    setLoading(true);
    try {
      const [cur, allTiers] = await Promise.all([
        apiFetch<any>("/api/v1/subscriptions/current"),
        apiFetch<any>("/api/v1/subscriptions/tiers"),
      ]);
      setSub(cur);
      setTiers(allTiers.tiers || []);
    } catch (err: any) {
      setMsg(err.message || "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBilling();
  }, []);

  async function handleSimulateSandboxPayment(provider: "FLUTTERWAVE" | "PAYSTACK", tier: string) {
    setSimulating(true);
    setMsg("");
    try {
      const endpoint = `/api/v1/subscriptions/webhook/${provider.toLowerCase()}`;
      const payload =
        provider === "FLUTTERWAVE"
          ? {
              event: "charge.completed",
              data: {
                id: Date.now(),
                tx_ref: `flw_sandbox_${Date.now()}`,
                amount: tier === "STARTER" ? 29000.0 : 75000.0,
                currency: "NGN",
                status: "successful",
                meta: { org_id: sub?.organization_id, tier },
              },
            }
          : {
              event: "charge.success",
              data: {
                reference: `pstk_sandbox_${Date.now()}`,
                amount: tier === "STARTER" ? 2900000 : 7500000,
                currency: "NGN",
                status: "success",
                metadata: { org_id: sub?.organization_id, tier },
              },
            };

      const res = await apiFetch<any>(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setMsg(`Sandbox verification confirmed: ${res.detail || "Subscription upgraded"}`);
      await loadBilling();
    } catch (err: any) {
      setMsg(err.message);
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 28, maxWidth: 960 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
          Subscription &amp; Entitlements
        </h1>
        <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
          Manage your organization tier, statutory application capacities, and payment gateway rails.
        </p>
      </div>

      {msg && <div className="pill pill-cyan" style={{ padding: "8px 14px" }}>{msg}</div>}

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
              <span style={{ fontSize: 22, fontWeight: 800, color: "#FFFFFF" }}>{sub.tier_name}</span>
              <StatusBadge status={sub.status} />
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Plan Price: <span className="gold-text mono">${sub.price_usd}/mo</span> · Renewal:{" "}
              {sub.renewal_date ? new Date(sub.renewal_date).toLocaleDateString() : "Active Entitlement"}
            </div>
          </div>

          <div className="row" style={{ gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
            <span className="row" style={{ gap: 4 }}>
              <Lock size={12} /> Sandbox Mode Active (No live charges)
            </span>
          </div>
        </div>
      )}

      {/* Tiers Grid */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Available Tier Entitlements</h2>

        <div className="grid-3" style={{ gap: 16 }}>
          {tiers.map((t) => {
            const isCurrent = sub?.tier === t.id;
            return (
              <div
                key={t.id}
                className={`card ${isCurrent ? "card-gold" : ""}`}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: 16,
                  padding: "24px 20px",
                  backgroundColor: "var(--bg-card)",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div className="row-between">
                    <strong style={{ fontSize: 16 }}>{t.name}</strong>
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

                {!isCurrent && t.id !== "FREE" && (
                  <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="btn btn-sm"
                      style={{ flex: 1 }}
                      disabled={simulating}
                      onClick={() => handleSimulateSandboxPayment("PAYSTACK", t.id)}
                    >
                      Paystack
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1 }}
                      disabled={simulating}
                      onClick={() => handleSimulateSandboxPayment("FLUTTERWAVE", t.id)}
                    >
                      Flutterwave
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
