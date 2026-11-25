import React, { useEffect, useState } from "react";
import { User, Building2, ShieldCheck, CheckCircle2, Lock, Sparkles, TrendingUp, DollarSign } from "lucide-react";
import { Organization } from "../types";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";

interface AccountPageProps {
  onNavigate: (route: string) => void;
}

export const AccountPage: React.FC<AccountPageProps> = () => {
  const { user } = useAuth();
  const [org, setOrg] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("Nigeria");
  const [stateLocation, setStateLocation] = useState("Abuja (FCT)");
  const [sector, setSector] = useState("Technology");
  const [stage, setStage] = useState("SEED");
  const [revenueNgn, setRevenueNgn] = useState<number>(0);
  const [cacRegistered, setCacRegistered] = useState(true);
  const [yearsInOperation, setYearsInOperation] = useState<number>(1);
  const [femaleLed, setFemaleLed] = useState(false);
  const [youthLed, setYouthLed] = useState(true);
  const [goals, setGoals] = useState("");
  const [productsServices, setProductsServices] = useState("");
  const [targetCustomers, setTargetCustomers] = useState("");
  const [businessModel, setBusinessModel] = useState("B2B");
  const [growthObjectives, setGrowthObjectives] = useState("");
  const [intendedUseOfFunds, setIntendedUseOfFunds] = useState("");
  const [readinessScore, setReadinessScore] = useState<number>(0);
  const [readinessLevel, setReadinessLevel] = useState<string>("EMERGING");
  const [msg, setMsg] = useState("");

  async function loadOrg() {
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/account/organization");
      setOrg(res);
      setName(res.name);
      setCountry(res.country);
      setStateLocation(res.state_location);
      setSector(res.sector);
      setStage(res.stage);
      setRevenueNgn(res.annual_revenue_ngn || 0);
      setCacRegistered(res.cac_registered ?? true);
      setYearsInOperation(res.years_in_operation || 1);
      setFemaleLed(Boolean(res.female_led));
      setYouthLed(res.youth_led ?? true);
      setGoals(res.funding_goals || "");
      setProductsServices(res.products_services || "");
      setTargetCustomers(res.target_customers || "");
      setBusinessModel(res.business_model || "B2B");
      setGrowthObjectives(res.growth_objectives || "");
      setIntendedUseOfFunds(res.intended_use_of_funds || "");
      setReadinessScore(res.readiness_score || 0);
      setReadinessLevel(res.readiness_level || "EMERGING");
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOrg();
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      const updated = await apiFetch<any>("/api/v1/account/organization", {
        method: "PUT",
        body: JSON.stringify({
          name,
          country,
          state_location: stateLocation,
          sector,
          stage,
          annual_revenue_ngn: Number(revenueNgn),
          cac_registered: cacRegistered,
          years_in_operation: Number(yearsInOperation),
          female_led: femaleLed,
          youth_led: youthLed,
          funding_goals: goals,
          products_services: productsServices,
          target_customers: targetCustomers,
          business_model: businessModel,
          growth_objectives: growthObjectives,
          intended_use_of_funds: intendedUseOfFunds,
        }),
      });
      setReadinessScore(updated.readiness_score || 0);
      setReadinessLevel(updated.readiness_level || "EMERGING");
      setMsg("Organization profile & AI readiness updated successfully.");
      setTimeout(() => setMsg(""), 4000);
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, paddingBottom: 60, display: "flex", flexDirection: "column", gap: 24, maxWidth: 920 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
          Organization Profile &amp; Business Intelligence
        </h1>
        <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
          Your profile parameters power CARAVAN's AI Copilot, automated eligibility matching, and application underwriting.
        </p>
      </div>

      {msg && <div className="pill pill-gold" style={{ padding: "8px 14px", alignSelf: "flex-start" }}>{msg}</div>}

      {/* Account Identity & Live Readiness Score Banner */}
      <div className="grid-2" style={{ gap: 16 }}>
        {user && (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14 }}>
            <div className="row" style={{ gap: 14 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "var(--radius-full)",
                  backgroundColor: "#161616",
                  border: "1.5px solid var(--accent-gold)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  color: "var(--accent-gold-bright)",
                  fontSize: 16,
                }}
              >
                {user.full_name ? user.full_name[0] : "U"}
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#FFFFFF" }}>{user.full_name}</div>
                <div className="muted" style={{ fontSize: 12 }}>{user.email}</div>
              </div>
            </div>
            <span className="pill pill-gold">{user.role}</span>
          </div>
        )}

        {/* AI Readiness Score Gauge */}
        <div
          className="card card-gold"
          style={{
            backgroundColor: "var(--bg-secondary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 24px",
          }}
        >
          <div>
            <div className="row" style={{ gap: 6, fontSize: 12, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
              <Sparkles size={14} /> CARAVAN Funding Readiness
            </div>
            <div className="mono gold-text" style={{ fontSize: 28, fontWeight: 800, marginTop: 4 }}>
              {readinessScore} <span style={{ fontSize: 14, color: "var(--text-muted)" }}>/ 100</span>
            </div>
            <div className="muted" style={{ fontSize: 11, textTransform: "capitalize" }}>
              Status: {readinessLevel.replace(/_/g, " ").toLowerCase()}
            </div>
          </div>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: "50%",
              backgroundColor: "rgba(198, 157, 73, 0.15)",
              border: "2px solid #C69D49",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ShieldCheck size={26} color="#C69D49" />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading organization details...
        </div>
      ) : (
        <form onSubmit={handleSave} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#FFFFFF", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 10 }}>
            1. Corporate Governance &amp; Registration
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Organization Legal / Trade Name *</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Country of Incorporation</label>
              <select className="input" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="Nigeria">Nigeria</option>
                <option value="Ghana">Ghana</option>
                <option value="Kenya">Kenya</option>
                <option value="Rwanda">Rwanda</option>
                <option value="United Kingdom">United Kingdom</option>
                <option value="United States">United States</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">State / Regional Location</label>
              <input className="input" value={stateLocation} onChange={(e) => setStateLocation(e.target.value)} />
            </div>
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Industry Sector</label>
              <select className="input" value={sector} onChange={(e) => setSector(e.target.value)}>
                <option value="Technology">Technology &amp; Software</option>
                <option value="FinTech">FinTech &amp; Financial Services</option>
                <option value="AgriTech">AgriTech &amp; Food Processing</option>
                <option value="HealthTech">HealthTech &amp; Life Sciences</option>
                <option value="CleanTech">CleanTech &amp; Renewable Energy</option>
                <option value="Manufacturing">Light Manufacturing &amp; Industrial</option>
                <option value="Commerce">Commerce, Retail &amp; FMCG</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Venture Operating Stage</label>
              <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
                <option value="IDEA">Idea / Concept</option>
                <option value="SEED">Pre-Seed / Seed</option>
                <option value="EARLY_GROWTH">Early Growth (Post-Revenue)</option>
                <option value="EXPANSION">Expansion / Scale</option>
              </select>
            </div>
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Annual Revenue (NGN ₦)</label>
              <input
                type="number"
                className="input"
                value={revenueNgn}
                onChange={(e) => setRevenueNgn(Number(e.target.value))}
                placeholder="e.g. 25000000"
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Operating History (Years in Operation)</label>
              <input
                type="number"
                min={0}
                className="input"
                value={yearsInOperation}
                onChange={(e) => setYearsInOperation(Number(e.target.value))}
                placeholder="e.g. 3"
              />
            </div>
          </div>

          <div
            className="card"
            style={{
              backgroundColor: "var(--bg-secondary)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
              padding: 16,
            }}
          >
            <label className="row" style={{ gap: 8, fontSize: 13, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={cacRegistered}
                onChange={(e) => setCacRegistered(e.target.checked)}
                style={{ accentColor: "var(--accent-gold)" }}
              />
              <span>CAC Formally Registered Entity</span>
            </label>

            <label className="row" style={{ gap: 8, fontSize: 13, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={femaleLed}
                onChange={(e) => setFemaleLed(e.target.checked)}
                style={{ accentColor: "var(--accent-gold)" }}
              />
              <span>Women-Led / Female-Founded (51%+ Equity)</span>
            </label>

            <label className="row" style={{ gap: 8, fontSize: 13, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={youthLed}
                onChange={(e) => setYouthLed(e.target.checked)}
                style={{ accentColor: "var(--accent-gold)" }}
              />
              <span>Youth-Led (Founders aged 18–35)</span>
            </label>
          </div>

          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#FFFFFF", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 10, marginTop: 10 }}>
            2. Strategic Intelligence &amp; Proposition
          </h2>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Products &amp; Core Services Offering</label>
              <textarea
                className="input"
                rows={3}
                value={productsServices}
                onChange={(e) => setProductsServices(e.target.value)}
                placeholder="e.g. Solar-powered micro cold storage units and logistics tracking software for fresh produce."
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Target Customer Segments &amp; Market</label>
              <textarea
                className="input"
                rows={3}
                value={targetCustomers}
                onChange={(e) => setTargetCustomers(e.target.value)}
                placeholder="e.g. Agricultural cooperatives, tomato farming clusters in Kano/Kaduna, and urban supermarket chains."
              />
            </div>
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Business / Monetization Model</label>
              <select className="input" value={businessModel} onChange={(e) => setBusinessModel(e.target.value)}>
                <option value="B2B">B2B (Enterprise &amp; Commercial)</option>
                <option value="B2C">B2C (Consumer Retail)</option>
                <option value="B2B2C">B2B2C (Partner Channel)</option>
                <option value="MARKETPLACE">Two-Sided Marketplace</option>
                <option value="SAAS">SaaS &amp; Subscription Software</option>
                <option value="HARDWARE_SERVICE">Hardware-as-a-Service / Lease</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">12-Month Growth Objectives</label>
              <input
                className="input"
                value={growthObjectives}
                onChange={(e) => setGrowthObjectives(e.target.value)}
                placeholder="e.g. Deploy 50 new cold rooms and reach ₦50M ARR."
              />
            </div>
          </div>

          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#FFFFFF", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 10, marginTop: 10 }}>
            3. Capital Strategy &amp; Funding Allocation
          </h2>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Primary Funding Goals</label>
              <textarea
                className="input"
                rows={3}
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
                placeholder="e.g. Seeking $150,000 non-dilutive grant or low-interest concessionary DFI facility."
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Intended Granular Use of Funds</label>
              <textarea
                className="input"
                rows={3}
                value={intendedUseOfFunds}
                onChange={(e) => setIntendedUseOfFunds(e.target.value)}
                placeholder="e.g. 60% machinery procurement, 25% operational scale, 15% governance and regulatory compliance."
              />
            </div>
          </div>

          <button type="submit" className="btn" style={{ alignSelf: "flex-start", marginTop: 8 }}>
            Save Venture Profile &amp; Recalculate Readiness
          </button>
        </form>
      )}

      {/* Data Governance & Statutory Privacy Controls */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16, backgroundColor: "var(--bg-card)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#FFFFFF" }}>
            Data Privacy &amp; Statutory Portability (NDPA 2023 &amp; GDPR)
          </h2>
          <p className="muted" style={{ fontSize: 13 }}>
            You have the statutory right to export your complete venture dossiers and request cryptographic deletion of personal data.
          </p>
        </div>

        <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={async () => {
              try {
                const data = await apiFetch<any>("/api/v1/account/export-data");
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `caravan-venture-export-${new Date().toISOString().split("T")[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
                setMsg("Customer data export successfully downloaded.");
                setTimeout(() => setMsg(""), 4000);
              } catch (err: any) {
                setMsg(err.message || "Failed to export data.");
              }
            }}
          >
            Export Venture Data (JSON)
          </button>

          <button
            type="button"
            className="btn btn-danger"
            style={{ backgroundColor: "rgba(225, 29, 72, 0.15)", color: "#FDA4AF", border: "1px solid rgba(225, 29, 72, 0.4)" }}
            onClick={async () => {
              const confirmText = prompt("To confirm account deletion under NDPA / GDPR, type DELETE in all capital letters:");
              if (confirmText === "DELETE") {
                try {
                  const res = await apiFetch<any>("/api/v1/account/delete-request", {
                    method: "POST",
                    body: JSON.stringify({ confirmation: "DELETE", reason: "Customer self-service requested deletion" }),
                  });
                  alert(res.message || "Account deletion scheduled.");
                } catch (err: any) {
                  alert(err.message || "Deletion request failed.");
                }
              }
            }}
          >
            Request Account Deletion
          </button>
        </div>
      </div>
    </div>
  );
};
