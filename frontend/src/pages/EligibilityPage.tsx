import React, { useEffect, useState } from "react";
import { Sparkles, CheckCircle2, AlertCircle, ArrowRight, RefreshCw, Award } from "lucide-react";
import { EligibilityAssessment } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge, EmptyState } from "../components/ui/DesignSystem";

interface EligibilityPageProps {
  onNavigate: (route: string) => void;
}

export const EligibilityPage: React.FC<EligibilityPageProps> = ({ onNavigate }) => {
  const [recommendations, setRecommendations] = useState<EligibilityAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  async function loadRecommendations() {
    setLoading(true);
    setMsg("");
    try {
      const res = await apiFetch<any>("/api/v1/eligibility/recommendations");
      setRecommendations(res.recommendations || []);
    } catch (err: any) {
      setMsg(err.message || "Failed to load eligibility matching.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRecommendations();
  }, []);

  async function handleStartApp(oppId: string) {
    try {
      await apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({ opportunity_id: oppId, notes: "Created from Eligibility Matching" }),
      });
      onNavigate("applications");
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            Eligibility Matching Scorecard
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Evaluated against your corporate structure, geography, sector, operating stage, and revenue.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadRecommendations}
          disabled={loading}
        >
          <RefreshCw size={13} /> Re-evaluate Scorecard
        </button>
      </div>

      {msg && <div className="pill pill-rose" style={{ padding: "8px 14px" }}>{msg}</div>}

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 48 }}>
          Evaluating institutional criteria against your organization profile...
        </div>
      ) : recommendations.length === 0 ? (
        <EmptyState
          icon={<Award size={36} />}
          title="No eligibility scorecards available"
          description="Complete your Organization Profile to generate automated eligibility scores against institutional facilities."
          actionLabel="Complete Profile"
          onAction={() => onNavigate("account")}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {recommendations.map((rec) => {
            const isStrong = rec.recommendation_level === "STRONG";
            return (
              <div
                key={rec.assessment_id}
                className={`card ${isStrong ? "card-gold" : ""}`}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                  padding: "20px 24px",
                  backgroundColor: "var(--bg-card)",
                }}
              >
                <div className="row-between" style={{ flexWrap: "wrap", gap: 14 }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "#FFFFFF" }}>
                      {rec.opportunity_title}
                    </h3>
                    <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{rec.provider}</div>
                  </div>

                  <div className="row" style={{ gap: 14 }}>
                    <div style={{ textAlign: "right" }}>
                      <span className="mono gold-text" style={{ fontSize: 20, fontWeight: 800 }}>
                        {rec.match_score}/100
                      </span>
                      <div className="muted" style={{ fontSize: 11 }}>Match Score</div>
                    </div>
                    <StatusBadge status={rec.recommendation_level} />
                  </div>
                </div>

                {/* Criteria Breakdown */}
                {rec.criteria_breakdown && (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                      gap: 10,
                      backgroundColor: "var(--bg-secondary)",
                      padding: 14,
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    {Object.entries(rec.criteria_breakdown).map(([key, item]) => (
                      <div key={key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                        {item.matched ? (
                          <CheckCircle2 size={14} color="var(--status-success-text)" />
                        ) : (
                          <AlertCircle size={14} color="var(--status-warning-text)" />
                        )}
                        <span style={{ textTransform: "capitalize", fontWeight: 600 }}>{key}:</span>
                        <span className="muted">{item.reason}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => handleStartApp(rec.opportunity_id)}
                  >
                    Prepare Application <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
