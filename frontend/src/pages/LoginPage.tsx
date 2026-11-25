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

  const [mode, setMode] = useState<"login" | "forgot" | "reset">("login");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [infoMsg, setInfoMsg] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInfoMsg("");
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

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInfoMsg("");
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: email.trim() }),
      });
      setInfoMsg(res.message);
      if (res.reset_token) {
        setResetToken(res.reset_token);
        setMode("reset");
      }
    } catch (err: any) {
      setError(err.message || "Failed to request password recovery.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInfoMsg("");
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token: resetToken.trim(), new_password: newPassword }),
      });
      setInfoMsg(res.message);
      setMode("login");
      setPassword("");
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
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
            {mode === "login" && "Sign In to CARAVAN"}
            {mode === "forgot" && "Recover Your Password"}
            {mode === "reset" && "Set New Password"}
          </h1>
          <p className="muted" style={{ fontSize: 13, maxWidth: 320 }}>
            {mode === "login" && "Access institutional funding intelligence and application pipelines."}
            {mode === "forgot" && "Enter your registered email to receive secure recovery instructions."}
            {mode === "reset" && "Enter your reset token and your new secure password."}
          </p>
        </div>

        {error && (
          <div className="pill pill-rose" style={{ justifySelf: "center", textAlign: "center", padding: "8px 14px", width: "100%", justifyContent: "center" }}>
            {error}
          </div>
        )}

        {infoMsg && (
          <div className="pill pill-emerald" style={{ justifySelf: "center", textAlign: "center", padding: "8px 14px", width: "100%", justifyContent: "center" }}>
            {infoMsg}
          </div>
        )}

        {mode === "login" && (
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
              <div className="row-between">
                <label className="form-label">Password *</label>
                <button
                  type="button"
                  className="muted font-bold"
                  style={{ fontSize: 12, cursor: "pointer", background: "none", border: "none", color: "var(--accent-gold-bright)" }}
                  onClick={() => {
                    setError("");
                    setInfoMsg("");
                    setMode("forgot");
                  }}
                >
                  Forgot Password?
                </button>
              </div>
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
        )}

        {mode === "forgot" && (
          <form onSubmit={handleForgotPassword} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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

            <button type="submit" className="btn btn-lg" disabled={loading} style={{ marginTop: 8 }}>
              {loading ? "Dispatching..." : "Send Recovery Link"} <ArrowRight size={14} />
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setError("");
                setInfoMsg("");
                setMode("login");
              }}
            >
              Back to Sign In
            </button>
          </form>
        )}

        {mode === "reset" && (
          <form onSubmit={handleResetPassword} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Reset Token *</label>
              <input
                className="input mono"
                placeholder="Paste token received in email"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">New Secure Password *</label>
              <input
                type="password"
                className="input"
                placeholder="••••••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-lg" disabled={loading} style={{ marginTop: 8 }}>
              {loading ? "Updating..." : "Update Password"} <ArrowRight size={14} />
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setError("");
                setInfoMsg("");
                setMode("login");
              }}
            >
              Back to Sign In
            </button>
          </form>
        )}

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

