import React, { useEffect, useState } from "react";
import { CreditCard, CheckCircle2, ShieldCheck, ArrowRight, Zap } from "lucide-react";
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
      const payload = provider === "FLUTTERWAVE"
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

      setMsg(`Sandbox checkout completed via ${provider}: Upgraded to ${res.tier}!`);
      loadBilling();
    } catch (err: any) {
      setMsg(err.message);
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24, maxWidth: 840 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800 }}>Subscriptions &amp; Payment Operations</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Manage your CARAVAN tier, billing receipts, and payment method via Paystack and Flutterwave sandbox.
        </p>
      </div>

      {msg && <div className="pill pill-emerald" style={{ alignSelf: "flex-start" }}>{msg}</div>}

      {/* Current plan card */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row-between">
          <div className="row" style={{ gap: 8 }}>
            <span className="pill pill-cyan">CURRENT PLAN</span>
            <StatusBadge status={sub?.status || "ACTIVE"} />
          </div>
          <span className="muted mono" style={{ fontSize: 12 }}>Provider: {sub?.billing_provider || "MANUAL"}</span>
        </div>

        <div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--accent-cyan)" }}>
            {sub?.tier_name || "Community Explorer"}
          </div>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            {sub?.price_usd === 0 ? "Free Plan" : `$${sub?.price_usd} / month`}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <strong style={{ fontSize: 12 }}>Active Entitlements:</strong>
          {(sub?.features || []).map((f, i) => (
            <div key={i} className="row" style={{ gap: 6, fontSize: 12 }}>
              <CheckCircle2 size={13} color="var(--accent-emerald)" />
              <span className="muted">{f}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sandbox Test Upgrades */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <strong style={{ fontSize: 14 }}>
            <Zap size={14} style={{ verticalAlign: "middle", marginRight: 4, color: "var(--accent-amber)" }} />
            Nigerian Payment Gateways (Sandbox Mode)
          </strong>
          <p className="muted" style={{ fontSize: 12, marginTop: 2 }}>
            Simulate instant webhook fulfillment and subscription provisioning for the Nigerian market.
          </p>
        </div>

        <div className="grid-2" style={{ gap: 12 }}>
          <div className="list-item" style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, backgroundColor: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}>
            <strong>Flutterwave Sandbox</strong>
            <span className="muted" style={{ fontSize: 12 }}>Test Starter Plan (₦29,000 / month)</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={simulating}
              onClick={() => handleSimulateSandboxPayment("FLUTTERWAVE", "STARTER")}
            >
              Test Flutterwave Checkout
            </button>
          </div>

          <div className="list-item" style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, backgroundColor: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}>
            <strong>Paystack Sandbox</strong>
            <span className="muted" style={{ fontSize: 12 }}>Test Growth Plan (₦75,000 / month)</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={simulating}
              onClick={() => handleSimulateSandboxPayment("PAYSTACK", "GROWTH")}
            >
              Test Paystack Checkout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
