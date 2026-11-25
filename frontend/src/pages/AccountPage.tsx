import React, { useEffect, useState } from "react";
import { User, Building2, ShieldCheck, CheckCircle2 } from "lucide-react";
import { Organization } from "../types";
import { apiFetch } from "../lib/api";

interface AccountPageProps {
  onNavigate: (route: string) => void;
}

export const AccountPage: React.FC<AccountPageProps> = () => {
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("Nigeria");
  const [stateLocation, setStateLocation] = useState("Abuja (FCT)");
  const [sector, setSector] = useState("Technology");
  const [stage, setStage] = useState("SEED");
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
          funding_goals: goals,
        }),
      });
      setMsg("Organization profile updated successfully.");
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24, maxWidth: 840 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800 }}>Organization Profile &amp; Venture Settings</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Your profile parameters power CARAVAN's automated eligibility matching engine.
        </p>
      </div>

      {msg && <div className="pill pill-cyan">{msg}</div>}

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading organization details...
        </div>
      ) : (
        <form onSubmit={handleSave} className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Organization Legal / Trade Name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Country of Incorporation</label>
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
              <label style={{ fontSize: 12, fontWeight: 600 }}>State / Regional Location</label>
              <input className="input" value={stateLocation} onChange={(e) => setStateLocation(e.target.value)} />
            </div>
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Industry Sector</label>
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
              <label style={{ fontSize: 12, fontWeight: 600 }}>Venture Operating Stage</label>
              <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
                <option value="IDEA">Idea / Concept</option>
                <option value="SEED">Pre-Seed / Seed</option>
                <option value="EARLY_GROWTH">Early Growth (Post-Revenue)</option>
                <option value="EXPANSION">Expansion / Scale</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Primary Funding Goals &amp; Capital Target</label>
            <textarea
              className="input"
              rows={3}
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              placeholder="e.g. Seeking $50,000 non-dilutive grant for CAC expansion and commercial pilot."
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
