import React from "react";
import { ShieldCheck, Globe, Lock } from "lucide-react";

interface FooterProps {
  onNavigate: (route: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  return (
    <footer style={{
      borderTop: "1px solid var(--border-subtle)",
      backgroundColor: "var(--bg-secondary)",
      padding: "48px 0 32px 0",
      marginTop: 80,
    }}>
      <div className="container" style={{ display: "flex", flexDirection: "column", gap: 32 }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: 24 }}>
          <div style={{ maxWidth: 360, display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="row" style={{ gap: 10 }}>
              <div style={{
                width: 28,
                height: 28,
                borderRadius: "var(--radius-sm)",
                background: "linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: 14,
                color: "#050b14",
              }}>
                C
              </div>
              <strong style={{ fontSize: 16, letterSpacing: "-0.01em" }}>CARAVAN</strong>
            </div>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
              Institutional funding intelligence, verified opportunity matching, and application operations platform for African high-growth enterprises and global scale.
            </p>
            <div className="row" style={{ gap: 6, fontSize: 11, color: "var(--accent-emerald)" }}>
              <ShieldCheck size={14} /> AEGIS Zero-Knowledge Provenance Verified
            </div>
          </div>

          <div className="row" style={{ gap: 48, flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>Platform</strong>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("how-it-works")}>How It Works</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>15 Categories</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("pricing")}>Pricing Tiers</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("discover")}>Funding Marketplace</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>Intelligence</strong>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Non-Dilutive Grants</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Concessionary Debt</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>DFI Facilities</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Venture Capital</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>Governance</strong>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("about")}>About CARAVAN</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("legal-privacy")}>Privacy & NDPR/GDPR</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("contact")}>Institutional Inquiries</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("support")}>Help & Support</button>
            </div>
          </div>
        </div>

        <div className="row-between" style={{
          borderTop: "1px solid var(--border-subtle)",
          paddingTop: 24,
          fontSize: 12,
          flexWrap: "wrap",
          gap: 12,
        }}>
          <div className="muted">
            &copy; 2026 CARAVAN Platform Ltd. All rights reserved. Registered under Nigerian Corporate Affairs Commission (CAC).
          </div>
          <div className="row" style={{ gap: 16, color: "var(--text-muted)" }}>
            <span className="row" style={{ gap: 4 }}><Lock size={12} /> TLS 1.3 256-bit Encryption</span>
            <span className="row" style={{ gap: 4 }}><Globe size={12} /> Abuja &amp; London Hubs</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
