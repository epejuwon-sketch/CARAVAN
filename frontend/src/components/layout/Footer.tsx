import React from "react";
import { ShieldCheck, Globe, Lock } from "lucide-react";
import { CaravanLogo } from "../brand/CaravanLogo";

interface FooterProps {
  onNavigate: (route: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--border-subtle)",
        backgroundColor: "var(--bg-secondary)",
        padding: "56px 0 36px 0",
        marginTop: 80,
      }}
    >
      <div className="container" style={{ display: "flex", flexDirection: "column", gap: 36 }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: 32, alignItems: "flex-start" }}>
          <div style={{ maxWidth: 380, display: "flex", flexDirection: "column", gap: 14 }}>
            <CaravanLogo size={26} wordmarkColor="white" onClick={() => onNavigate("home")} />
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.6, marginTop: 4 }}>
              Institutional funding intelligence, verified opportunity matching, and application operations platform for emerging African ventures and global scale.
            </p>
            <div className="row" style={{ gap: 6, fontSize: 11, color: "var(--accent-gold-bright)" }}>
              <ShieldCheck size={14} /> Cryptographic Provenance Verified
            </div>
          </div>

          <div className="row" style={{ gap: 48, flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
              <strong style={{ fontSize: 12, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Platform
              </strong>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("discover")}>Opportunities</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("how-it-works")}>How It Works</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>15 Categories</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("pricing")}>Pricing Tiers</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
              <strong style={{ fontSize: 12, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Intelligence
              </strong>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Non-Dilutive Grants</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Concessionary Debt</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>DFI Facilities</button>
              <button type="button" className="muted" style={{ textAlign: "left" }} onClick={() => onNavigate("categories")}>Venture Capital</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
              <strong style={{ fontSize: 12, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Company &amp; Legal
              </strong>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("about")}>About</button>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("privacy")}>Privacy Policy (NDPA)</button>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("terms")}>Terms of Service</button>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("refund")}>Refund Policy</button>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("cookies")}>Cookie Policy</button>
              <button type="button" className="muted" style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => onNavigate("operator")}>Operator Information</button>
              <button
                type="button"
                className="muted"
                style={{ textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0, color: "var(--accent-gold-bright)" }}
                onClick={() => window.dispatchEvent(new CustomEvent("open-cookie-preferences"))}
              >
                Cookie Preferences
              </button>
            </div>
          </div>
        </div>

        <div
          className="row-between"
          style={{
            borderTop: "1px solid var(--border-subtle)",
            paddingTop: 24,
            fontSize: 12,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div className="muted">
            &copy; 2026 CARAVAN Capital Intelligence Ltd. All rights reserved. &middot; <span className="mono" style={{ fontSize: 11 }}>Zero Fabricated Opportunities</span>
          </div>
          <div className="row" style={{ gap: 20, color: "var(--text-muted)", fontSize: 12 }}>
            <span className="row" style={{ gap: 5 }}><Lock size={12} /> TLS 1.3 Encryption</span>
            <span className="row" style={{ gap: 5 }}><Globe size={12} /> Abuja &amp; London Hubs</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
