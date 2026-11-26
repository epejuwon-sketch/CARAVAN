import React, { useState, useEffect } from "react";
import { ShieldCheck, Lock, X, Check, Settings, AlertCircle } from "lucide-react";

interface CookiePreferences {
  essential: boolean;
  functional: boolean;
  analytics: boolean;
  timestamp: string;
}

export const CookieConsentBanner: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [preferences, setPreferences] = useState<CookiePreferences>({
    essential: true,
    functional: false,
    analytics: false,
    timestamp: "",
  });

  useEffect(() => {
    try {
      const stored = localStorage.getItem("caravan_cookie_consent");
      if (!stored) {
        setVisible(true);
      } else {
        setPreferences(JSON.parse(stored));
      }
    } catch {
      setVisible(true);
    }

    const handleOpenModal = () => {
      setModalOpen(true);
      setVisible(true);
    };

    window.addEventListener("open-cookie-preferences", handleOpenModal);
    return () => window.removeEventListener("open-cookie-preferences", handleOpenModal);
  }, []);

  const savePreferences = (prefs: CookiePreferences) => {
    try {
      localStorage.setItem("caravan_cookie_consent", JSON.stringify(prefs));
    } catch {
      // ignore
    }
    setPreferences(prefs);
    setVisible(false);
    setModalOpen(false);
  };

  const handleAcceptAll = () => {
    const updated: CookiePreferences = {
      essential: true,
      functional: true,
      analytics: true,
      timestamp: new Date().toISOString(),
    };
    savePreferences(updated);
  };

  const handleRejectNonEssential = () => {
    const updated: CookiePreferences = {
      essential: true,
      functional: false,
      analytics: false,
      timestamp: new Date().toISOString(),
    };
    savePreferences(updated);
  };

  const handleSaveCustom = () => {
    savePreferences({
      ...preferences,
      essential: true,
      timestamp: new Date().toISOString(),
    });
  };

  if (!visible) return null;

  return (
    <>
      {/* Bottom Sticky Banner */}
      {!modalOpen && (
        <aside
          role="region"
          aria-label="Cookie and Privacy Consent"
          style={{
            position: "fixed",
            bottom: 16,
            left: 16,
            right: 16,
            maxWidth: 1100,
            margin: "0 auto",
            backgroundColor: "rgba(18, 20, 26, 0.98)",
            border: "1px solid var(--border-gold)",
            borderRadius: "var(--radius-lg)",
            padding: "18px 24px",
            boxShadow: "0 10px 40px rgba(0, 0, 0, 0.7)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14, maxWidth: 620 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-gold)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-gold-bright)",
                flexShrink: 0,
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <strong style={{ fontSize: 14, color: "#FFFFFF" }}>CARAVAN Privacy &amp; Data Sovereignty</strong>
              <p className="muted" style={{ fontSize: 12, marginTop: 2, lineHeight: 1.5 }}>
                We use strictly essential cookies for secure authentication and optional preferences to enhance your funding discovery. Zero cross-site advertising or third-party trackers are used.
              </p>
            </div>
          </div>

          <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setModalOpen(true)}
              style={{ fontSize: 12 }}
            >
              <Settings size={13} /> Customize
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleRejectNonEssential}
              style={{ fontSize: 12 }}
            >
              Reject Non-Essential
            </button>
            <button
              type="button"
              className="btn btn-sm"
              onClick={handleAcceptAll}
              style={{ fontSize: 12, fontWeight: 700 }}
            >
              Accept All
            </button>
          </div>
        </aside>
      )}

      {/* Preferences Modal */}
      {modalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cookie-modal-title"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(8px)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 580,
              width: "100%",
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-gold)",
              borderRadius: "var(--radius-lg)",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            <div className="row-between">
              <div className="row" style={{ gap: 10 }}>
                <ShieldCheck size={20} color="var(--accent-gold-bright)" />
                <strong id="cookie-modal-title" style={{ fontSize: 16, color: "#FFFFFF" }}>
                  Cookie &amp; Privacy Preferences
                </strong>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setModalOpen(false)}
                aria-label="Close cookie preferences modal"
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Essential */}
              <div className="list-item row-between" style={{ padding: "12px 16px" }}>
                <div>
                  <strong style={{ fontSize: 13, color: "#FFFFFF" }}>Strictly Essential Storage</strong>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    Necessary for user login, JWT session security, and anti-fraud CSRF controls.
                  </div>
                </div>
                <span className="pill pill-gold" style={{ fontSize: 10, fontWeight: 700 }}>
                  ALWAYS ACTIVE
                </span>
              </div>

              {/* Functional */}
              <div className="list-item row-between" style={{ padding: "12px 16px" }}>
                <div>
                  <strong style={{ fontSize: 13, color: "#FFFFFF" }}>Functional Preferences</strong>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    Remembers your opportunity filters, category sorting, and accessibility settings.
                  </div>
                </div>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={preferences.functional}
                    onChange={(e) => setPreferences({ ...preferences, functional: e.target.checked })}
                    style={{ width: 18, height: 18, accentColor: "var(--accent-gold)" }}
                  />
                </label>
              </div>

              {/* Analytics */}
              <div className="list-item row-between" style={{ padding: "12px 16px" }}>
                <div>
                  <strong style={{ fontSize: 13, color: "#FFFFFF" }}>Privacy-Preserving Telemetry</strong>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    Aggregated, non-identifying operational error rates and performance latency.
                  </div>
                </div>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={preferences.analytics}
                    onChange={(e) => setPreferences({ ...preferences, analytics: e.target.checked })}
                    style={{ width: 18, height: 18, accentColor: "var(--accent-gold)" }}
                  />
                </label>
              </div>
            </div>

            <div className="row-between" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 16, flexWrap: "wrap", gap: 10 }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleRejectNonEssential}
              >
                Reject Non-Essential
              </button>
              <div className="row" style={{ gap: 8 }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleSaveCustom}
                >
                  Save Preferences
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={handleAcceptAll}
                  style={{ fontWeight: 700 }}
                >
                  Accept All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
