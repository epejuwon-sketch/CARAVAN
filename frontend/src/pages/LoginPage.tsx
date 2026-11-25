import React, { useState } from "react";
import { Lock, Mail, ArrowRight, ShieldCheck } from "lucide-react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../lib/auth";

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
      onNavigate("discover");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 60, maxWidth: 440 }}>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{
            width: 44,
            height: 44,
            margin: "0 auto",
            borderRadius: "var(--radius-sm)",
            background: "linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            fontSize: 22,
            color: "#050b14",
          }}>
            C
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Sign in to CARAVAN</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Access institutional funding intelligence and application pipelines.
          </p>
        </div>

        {error && (
          <div className="pill pill-rose" style={{ justifySelf: "center", textAlign: "center", padding: "8px 12px" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
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

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 600 }}>Password</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? "Authenticating..." : "Sign In"} <ArrowRight size={14} />
          </button>
        </form>

        <div className="row-between" style={{ fontSize: 12, borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
          <span className="muted">Don't have an account?</span>
          <button type="button" style={{ color: "var(--accent-cyan)", fontWeight: 600 }} onClick={() => onNavigate("register")}>
            Create Account
          </button>
        </div>
      </div>
    </div>
  );
};
