import React, { useState } from "react";
import { Lock, Mail, ArrowRight, ShieldCheck } from "lucide-react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";
import { CaravanLogo } from "../components/brand/CaravanLogo";

interface LoginPageProps {
  onNavigate: (route: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      login(res.access_token, res.user);
      onNavigate(res.user?.role === "ADMIN" ? "admin" : "dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 60, maxWidth: 460 }}>
      <div className="card card-gold" style={{ display: "flex", flexDirection: "column", gap: 24, padding: "36px 32px", backgroundColor: "var(--bg-secondary)" }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <CaravanLogo size={38} layout="vertical" wordmarkColor="white" />
          <h1 style={{ fontSize: 20, fontWeight: 800, color: "#FFFFFF", marginTop: 6 }}>
            Sign In to CARAVAN
          </h1>
          <p className="muted" style={{ fontSize: 13, maxWidth: 320 }}>
            Access institutional funding intelligence and application pipelines.
          </p>
        </div>

        {error && (
          <div className="pill pill-rose" style={{ justifySelf: "center", textAlign: "center", padding: "8px 14px", width: "100%", justifyContent: "center" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Corporate Email Address *</label>
            <input
              type="email"
              className="input"
              placeholder="founder@venture.ng"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Password *</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn-lg" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? "Authenticating..." : "Sign In"} <ArrowRight size={14} />
          </button>
        </form>

        <div className="row-between" style={{ fontSize: 13, borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
          <span className="muted">Don't have an organization account?</span>
          <button
            type="button"
            className="gold-text font-bold"
            style={{ fontWeight: 700 }}
            onClick={() => onNavigate("register")}
          >
            Create Account
          </button>
        </div>
      </div>
    </div>
  );
};
