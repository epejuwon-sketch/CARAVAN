import React, { useEffect, useState } from "react";
import { User, Building2, ShieldCheck, CheckCircle2, Lock } from "lucide-react";
import { Organization } from "../types";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";

interface AccountPageProps {
  onNavigate: (route: string) => void;
}

export const AccountPage: React.FC<AccountPageProps> = () => {
  const { user } = useAuth();
  const [org, setOrg] = useState<Organization | null>(null);
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
      await apiFetch("/api/v1/account/organization", {
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
        }),
      });
      setMsg("Organization profile updated successfully.");
      setTimeout(() => setMsg(""), 4000);
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24, maxWidth: 840 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
          Organization Profile &amp; Venture Settings
        </h1>
        <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
          Your profile parameters power CARAVAN's automated eligibility matching engine and application workflows.
        </p>
      </div>

      {msg && <div className="pill pill-emerald" style={{ padding: "8px 14px" }}>{msg}</div>}

      {/* Account Identity Card */}
      {user && (
        <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          <div className="row" style={{ gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-full)",
                backgroundColor: "var(--accent-gold)",
                color: "#050505",
                fontWeight: 800,
                fontSize: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {user.full_name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>{user.full_name}</div>
              <div className="muted mono" style={{ fontSize: 12 }}>{user.email}</div>
            </div>
          </div>
          <span className="pill pill-gold">{user.role}</span>
        </div>
      )}

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading organization details...
        </div>
      ) : (
        <form onSubmit={handleSave} className="card" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
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
                <option value="Manufacturing">Light Manufacturing</option>
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

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Primary Funding Goals &amp; Capital Target</label>
            <textarea
              className="input"
              rows={3}
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              placeholder="e.g. Seeking $100,000 non-dilutive grant for production capacity expansion and commercial licensing."
            />
          </div>

          <button type="submit" className="btn" style={{ alignSelf: "flex-start", marginTop: 8 }}>
            Save Venture Profile
          </button>
        </form>
      )}
    </div>
  );
};
