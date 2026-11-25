import React, { useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";

interface RegisterPageProps {
  onNavigate: (route: string) => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigate }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [country, setCountry] = useState("Nigeria");
  const [sector, setSector] = useState("Technology");
  const [stage, setStage] = useState("SEED");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          organization_name: orgName.trim(),
          country,
          sector,
          stage,
        }),
      });
      login(res.access_token, res.user);
      onNavigate("discover");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please check inputs.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 40, maxWidth: 520 }}>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 6 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800 }}>Create Your CARAVAN Account</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Join forward-thinking ventures accessing verified institutional funding.
          </p>
        </div>

        {error && <div className="pill pill-rose" style={{ padding: "8px 12px" }}>{error}</div>}

        <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="grid-2" style={{ gap: 12 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Full Name</label>
              <input
                className="input"
                placeholder="Amara Nwosu"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Work Email</label>
              <input
                type="email"
                className="input"
                placeholder="founder@venture.ng"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Password (min 8 chars)</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Organization / Startup Name</label>
            <input
              className="input"
              placeholder="Nwosu AgriTech Solutions"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
            />
          </div>

          <div className="grid-3" style={{ gap: 8 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600 }}>Country</label>
              <select className="input" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="Nigeria">Nigeria</option>
                <option value="Ghana">Ghana</option>
                <option value="Kenya">Kenya</option>
                <option value="Rwanda">Rwanda</option>
                <option value="United Kingdom">United Kingdom</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600 }}>Sector</label>
              <select className="input" value={sector} onChange={(e) => setSector(e.target.value)}>
                <option value="Technology">Tech</option>
                <option value="FinTech">FinTech</option>
                <option value="AgriTech">AgriTech</option>
                <option value="HealthTech">Health</option>
                <option value="CleanTech">CleanTech</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600 }}>Stage</label>
              <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
                <option value="IDEA">Idea</option>
                <option value="SEED">Seed</option>
                <option value="EARLY_GROWTH">Growth</option>
                <option value="EXPANSION">Scale</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? "Creating Account..." : "Complete Registration"} <ArrowRight size={14} />
          </button>
        </form>

        <div className="row-between" style={{ fontSize: 12, borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
          <span className="muted">Already registered?</span>
          <button type="button" style={{ color: "var(--accent-cyan)", fontWeight: 600 }} onClick={() => onNavigate("login")}>
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
};
