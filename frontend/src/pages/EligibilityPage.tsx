import React, { useEffect, useState } from "react";
import { Sparkles, CheckCircle2, AlertCircle, ArrowRight, RefreshCw } from "lucide-react";
import { EligibilityAssessment } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge } from "../components/ui/DesignSystem";

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
          <h1 style={{ fontSize: 28, fontWeight: 800 }}>Smart Eligibility Matching Scorecard</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Evaluated against your CAC corporate structure, geography, sector, operating stage, and revenue.
          </p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={loadRecommendations} disabled={loading}>
          <RefreshCw size={13} /> Re-evaluate Scorecard
        </button>
      </div>

      {msg && <div className="pill pill-rose">{msg}</div>}

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Computing eligibility match scores against verified institutional programs...
        </div>
      ) : recommendations.length === 0 ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          No eligibility evaluations found. Update your organization profile or browse the marketplace.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {recommendations.map((rec) => (
            <div
              key={rec.assessment_id}
              className="card"
              style={{ display: "flex", flexDirection: "column", gap: 14 }}
            >
              <div className="row-between" style={{ flexWrap: "wrap", gap: 12 }}>
                <div>
                  <strong style={{ fontSize: 16 }}>{rec.opportunity_title}</strong>
                  <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{rec.provider}</div>
                </div>

                <div className="row" style={{ gap: 10 }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: rec.match_score >= 80 ? "var(--accent-emerald)" : "var(--accent-cyan)" }}>
                      {rec.match_score.toFixed(0)}% Match
                    </div>
                    <StatusBadge status={rec.recommendation_level} />
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => handleStartApp(rec.opportunity_id)}
                  >
                    Apply Now <ArrowRight size={12} />
                  </button>
                </div>
              </div>

              {/* Criteria breakdown */}
              <div className="grid-3" style={{ gap: 10 }}>
                {Object.entries(rec.criteria_breakdown || {}).map(([key, val]: [string, any]) => (
                  <div
                    key={key}
                    style={{
                      padding: 10,
                      borderRadius: "var(--radius-sm)",
                      backgroundColor: "var(--bg-secondary)",
                      border: "1px solid var(--border-subtle)",
                      fontSize: 12,
                    }}
                  >
                    <div className="row-between" style={{ textTransform: "capitalize", fontWeight: 600 }}>
                      <span>{key.replace("_", " ")}</span>
                      <span className="mono" style={{ color: val.score > 0 ? "var(--accent-emerald)" : "var(--accent-rose)" }}>
                        +{val.score} pts
                      </span>
                    </div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{val.reason}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
