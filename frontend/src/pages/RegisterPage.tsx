import React, { useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";
import { CaravanLogo } from "../components/brand/CaravanLogo";

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
      onNavigate("dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please check inputs.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 40, maxWidth: 540 }}>
      <div className="card card-gold" style={{ display: "flex", flexDirection: "column", gap: 24, padding: "36px 32px", backgroundColor: "var(--bg-secondary)" }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <CaravanLogo size={38} layout="vertical" wordmarkColor="white" />
          <h1 style={{ fontSize: 20, fontWeight: 800, color: "#FFFFFF", marginTop: 6 }}>
            Create Your Organization Account
          </h1>
          <p className="muted" style={{ fontSize: 13, maxWidth: 360 }}>
            Join ventures accessing verified institutional funding intelligence.
          </p>
        </div>

        {error && (
          <div className="pill pill-rose" style={{ padding: "8px 14px", width: "100%", justifyContent: "center" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="grid-2" style={{ gap: 12 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Full Name *</label>
              <input
                className="input"
                placeholder="Amara Nwosu"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Work Email *</label>
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

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Password (min 8 characters) *</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Organization / Startup Legal Name *</label>
            <input
              className="input"
              placeholder="e.g. Acme Scale Ltd"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
            />
          </div>

          <div className="grid-3" style={{ gap: 10 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Country</label>
              <select className="input" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="Nigeria">Nigeria</option>
                <option value="Ghana">Ghana</option>
                <option value="Kenya">Kenya</option>
                <option value="Rwanda">Rwanda</option>
                <option value="United Kingdom">United Kingdom</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Sector</label>
              <select className="input" value={sector} onChange={(e) => setSector(e.target.value)}>
                <option value="Technology">Technology</option>
                <option value="FinTech">FinTech</option>
                <option value="AgriTech">AgriTech</option>
                <option value="HealthTech">HealthTech</option>
                <option value="CleanTech">CleanTech</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Stage</label>
              <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
                <option value="IDEA">Idea</option>
                <option value="SEED">Seed</option>
                <option value="EARLY_GROWTH">Growth</option>
                <option value="EXPANSION">Expansion</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-lg" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? "Registering..." : "Create Organization Account"} <ArrowRight size={14} />
          </button>
        </form>

        <div className="row-between" style={{ fontSize: 13, borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
          <span className="muted">Already registered?</span>
          <button
            type="button"
            className="gold-text font-bold"
            style={{ fontWeight: 700 }}
            onClick={() => onNavigate("login")}
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
};
