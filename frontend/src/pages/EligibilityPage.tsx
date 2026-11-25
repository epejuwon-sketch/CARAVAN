import React, { useEffect, useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  Award,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Check,
  X,
} from "lucide-react";
import { EligibilityAssessment } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge, EmptyState } from "../components/ui/DesignSystem";

interface EligibilityPageProps {
  onNavigate: (route: string) => void;
}

export const EligibilityPage: React.FC<EligibilityPageProps> = ({ onNavigate }) => {
  const [recommendations, setRecommendations] = useState<EligibilityAssessment[]>([]);
  const [strongMatches, setStrongMatches] = useState<EligibilityAssessment[]>([]);
  const [possibleMatches, setPossibleMatches] = useState<EligibilityAssessment[]>([]);
  const [ineligible, setIneligible] = useState<EligibilityAssessment[]>([]);
  const [activeTab, setActiveTab] = useState<"ALL" | "STRONG" | "POSSIBLE" | "INELIGIBLE">("ALL");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  async function loadRecommendations() {
    setLoading(true);
    setMsg("");
    try {
      const res = await apiFetch<any>("/api/v1/eligibility/recommendations");
      setRecommendations(res.recommendations || []);
      setStrongMatches(res.strong_matches || []);
      setPossibleMatches(res.possible_matches || []);
      setIneligible(res.ineligible_opportunities || []);
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

  const displayedList =
    activeTab === "STRONG"
      ? strongMatches
      : activeTab === "POSSIBLE"
      ? possibleMatches
      : activeTab === "INELIGIBLE"
      ? ineligible
      : recommendations;

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            Eligibility Matching Intelligence
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Transparent assessment of your corporate structure, jurisdiction, CAC status, operating stage, and financials against verified institutional requirements. Zero synthetic scores.
          </p>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate("account")}
          >
            Update Venture Profile
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadRecommendations}
            disabled={loading}
          >
            <RefreshCw size={13} /> Re-evaluate Matching
          </button>
        </div>
      </div>

      {msg && <div className="pill pill-rose" style={{ padding: "8px 14px" }}>{msg}</div>}

      {/* Tabs */}
      <div className="row" style={{ gap: 10, flexWrap: "wrap", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 12 }}>
        <button
          type="button"
          className={`btn btn-sm ${activeTab === "ALL" ? "" : "btn-secondary"}`}
          onClick={() => setActiveTab("ALL")}
        >
          All Opportunities ({recommendations.length})
        </button>
        <button
          type="button"
          className={`btn btn-sm ${activeTab === "STRONG" ? "" : "btn-secondary"}`}
          onClick={() => setActiveTab("STRONG")}
        >
          <ShieldCheck size={14} color="#10B981" /> Strong Matches ({strongMatches.length})
        </button>
        <button
          type="button"
          className={`btn btn-sm ${activeTab === "POSSIBLE" ? "" : "btn-secondary"}`}
          onClick={() => setActiveTab("POSSIBLE")}
        >
          <Sparkles size={14} color="#FBBF24" /> Possible Matches ({possibleMatches.length})
        </button>
        <button
          type="button"
          className={`btn btn-sm ${activeTab === "INELIGIBLE" ? "" : "btn-secondary"}`}
          onClick={() => setActiveTab("INELIGIBLE")}
        >
          <ShieldAlert size={14} color="#F43F5E" /> Ineligible / Closed ({ineligible.length})
        </button>
      </div>

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 48 }}>
          Evaluating institutional eligibility criteria against your organization profile...
        </div>
      ) : displayedList.length === 0 ? (
        <EmptyState
          icon={<Award size={36} />}
          title="No opportunities in this category"
          description="Adjust your Venture Profile settings or browse all verified opportunities in the Marketplace."
          actionLabel="Go to Marketplace"
          onAction={() => onNavigate("marketplace")}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {displayedList.map((rec) => {
            const isStrong = rec.recommendation_level === "STRONG";
            const isIneligible = rec.recommendation_level === "INELIGIBLE" || rec.is_disqualified;
            const breakdown = rec.criteria_breakdown?.breakdown || rec.criteria_breakdown || {};
            const strengths = rec.strengths || rec.criteria_breakdown?.strengths || [];
            const missingReqs = rec.missing_requirements || rec.criteria_breakdown?.missing_requirements || [];
            const disqualifications = rec.disqualifications || rec.criteria_breakdown?.disqualifications || [];
            const isClosed = rec.live_status === "CLOSED" || rec.criteria_breakdown?.live_status === "CLOSED";
            const conditions = rec.criteria_breakdown?.important_conditions || "";
            const whyMatches = rec.criteria_breakdown?.why_matches || (rec as any).why_matches || "";
            const whyUnavailable = rec.criteria_breakdown?.why_unavailable || (rec as any).why_unavailable || "";
            const unknownCriteria = rec.criteria_breakdown?.unknown_criteria || (rec as any).unknown_criteria || [];
            const nextSteps = rec.criteria_breakdown?.next_steps || (rec as any).next_steps || [];
            const disclaimer = rec.criteria_breakdown?.disclaimer || (rec as any).disclaimer || "CARAVAN provides an algorithmic eligibility estimate based on published statutory criteria. Final funding decisions are made exclusively by the official program provider.";

            return (
              <div
                key={rec.assessment_id}
                className={`card ${isStrong ? "card-gold" : ""}`}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                  padding: "22px 24px",
                  backgroundColor: "var(--bg-card)",
                  border: isStrong
                    ? "1px solid var(--border-gold)"
                    : isIneligible
                    ? "1px solid rgba(244, 63, 94, 0.3)"
                    : "1px solid var(--border-subtle)",
                }}
              >
                {/* Header */}
                <div className="row-between" style={{ flexWrap: "wrap", gap: 14 }}>
                  <div style={{ flex: "1 1 300px" }}>
                    <div className="row" style={{ gap: 8, alignItems: "center" }}>
                      <h3 style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF" }}>
                        {rec.opportunity_title}
                      </h3>
                      {isClosed && <span className="pill pill-rose">CLOSED</span>}
                    </div>
                    <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
                      {rec.provider} {rec.amount_display ? `· ${rec.amount_display}` : ""}
                    </div>
                  </div>

                  <div className="row" style={{ gap: 16, alignItems: "center" }}>
                    <div style={{ textAlign: "right" }}>
                      <span
                        className="mono"
                        style={{
                          fontSize: 22,
                          fontWeight: 800,
                          color: isStrong
                            ? "var(--accent-gold-bright)"
                            : isIneligible
                            ? "var(--status-danger-text)"
                            : "var(--text-primary)",
                        }}
                      >
                        {Math.round(rec.match_score)}%
                      </span>
                      <div className="muted" style={{ fontSize: 11 }}>Eligibility Match</div>
                    </div>
                    <StatusBadge status={rec.recommendation_level} />
                  </div>
                </div>

                {/* Explainability Summary */}
                {(whyMatches || whyUnavailable) && (
                  <div
                    style={{
                      backgroundColor: "var(--bg-secondary)",
                      borderRadius: "var(--radius-sm)",
                      padding: "10px 14px",
                      fontSize: 13,
                      borderLeft: isIneligible ? "3px solid #F43F5E" : "3px solid var(--accent-gold)",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: "#FFFFFF", marginBottom: 2 }}>
                      {isIneligible ? "Why Unmatched / Unavailable:" : "Why You Match:"}
                    </div>
                    <div className="muted" style={{ lineHeight: 1.5 }}>
                      {isIneligible ? whyUnavailable : whyMatches}
                    </div>
                  </div>
                )}

                {/* Important Conditions / Fee Disclosures */}
                {conditions && (
                  <div
                    style={{
                      backgroundColor: "rgba(234, 179, 8, 0.08)",
                      border: "1px solid rgba(234, 179, 8, 0.25)",
                      borderRadius: "var(--radius-sm)",
                      padding: "10px 14px",
                      fontSize: 12,
                      color: "var(--text-secondary)",
                      lineHeight: 1.5,
                    }}
                  >
                    <strong style={{ color: "#FBBF24", display: "inline-block", marginRight: 6 }}>
                      Important Condition / Fee Disclosure:
                    </strong>
                    {conditions}
                  </div>
                )}

                {/* Disqualification Alerts */}
                {disqualifications.length > 0 && (
                  <div
                    style={{
                      backgroundColor: "rgba(244, 63, 94, 0.08)",
                      border: "1px solid rgba(244, 63, 94, 0.25)",
                      borderRadius: "var(--radius-sm)",
                      padding: "10px 14px",
                    }}
                  >
                    <strong style={{ color: "#F43F5E", fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
                      <AlertCircle size={13} /> Disqualification Reasons:
                    </strong>
                    <ul style={{ margin: "6px 0 0 18px", padding: 0, fontSize: 12, color: "#FCA5A5" }}>
                      {disqualifications.map((d: string, i: number) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Strengths & Missing Elements */}
                <div className="grid-2" style={{ gap: 14 }}>
                  {strengths.length > 0 && (
                    <div
                      style={{
                        backgroundColor: "var(--bg-secondary)",
                        padding: 12,
                        borderRadius: "var(--radius-sm)",
                        fontSize: 12,
                      }}
                    >
                      <strong style={{ color: "#10B981", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                        <CheckCircle2 size={13} /> Satisfied Criteria ({strengths.length}):
                      </strong>
                      <ul style={{ margin: 0, paddingLeft: 16, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
                        {strengths.map((s: string, i: number) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {missingReqs.length > 0 && (
                    <div
                      style={{
                        backgroundColor: "var(--bg-secondary)",
                        padding: 12,
                        borderRadius: "var(--radius-sm)",
                        fontSize: 12,
                      }}
                    >
                      <strong style={{ color: "#FBBF24", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                        <AlertCircle size={13} /> Missing / Recommended Criteria:
                      </strong>
                      <ul style={{ margin: 0, paddingLeft: 16, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
                        {missingReqs.map((m: string, i: number) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Unknown Criteria if present */}
                {unknownCriteria.length > 0 && (
                  <div
                    style={{
                      backgroundColor: "var(--bg-secondary)",
                      padding: "8px 12px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 11,
                      color: "var(--text-secondary)",
                    }}
                  >
                    <span style={{ color: "#FBBF24", fontWeight: 700 }}>Note on Profile Completeness:</span>{" "}
                    {unknownCriteria.join(" ")}
                  </div>
                )}

                {/* Next Steps */}
                {nextSteps.length > 0 && (
                  <div
                    style={{
                      backgroundColor: "var(--bg-secondary)",
                      padding: 12,
                      borderRadius: "var(--radius-sm)",
                      fontSize: 12,
                    }}
                  >
                    <strong style={{ color: "var(--accent-gold-bright)", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                      <Sparkles size={13} /> What You Can Do Next:
                    </strong>
                    <ul style={{ margin: 0, paddingLeft: 16, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
                      {nextSteps.map((step: string, i: number) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Criteria Breakdown Grid */}
                {breakdown && Object.keys(breakdown).length > 0 && (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
                      gap: 8,
                      backgroundColor: "var(--bg-secondary)",
                      padding: 12,
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border-subtle)",
                      fontSize: 11,
                    }}
                  >
                    {Object.entries(breakdown).map(([k, val]: [string, any]) => {
                      if (typeof val !== "object" || val === null || !("matched" in val)) return null;
                      const isMatch = val.matched === true;
                      const isPartial = val.matched === "partial";
                      return (
                        <div key={k} style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
                          {isMatch ? (
                            <Check size={13} color="#10B981" style={{ marginTop: 2, flexShrink: 0 }} />
                          ) : isPartial ? (
                            <Sparkles size={13} color="#FBBF24" style={{ marginTop: 2, flexShrink: 0 }} />
                          ) : (
                            <X size={13} color="#F43F5E" style={{ marginTop: 2, flexShrink: 0 }} />
                          )}
                          <div>
                            <span style={{ textTransform: "capitalize", fontWeight: 700, color: "#E2E8F0" }}>{k}:</span>{" "}
                            <span className="muted">{val.reason || "Evaluated"}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Disclaimer */}
                <div className="muted" style={{ fontSize: 11, fontStyle: "italic", paddingTop: 4 }}>
                  {disclaimer}
                </div>

                {/* Footer Actions */}
                <div className="row-between" style={{ alignItems: "center", flexWrap: "wrap", gap: 12, paddingTop: 4 }}>
                  <div className="row" style={{ gap: 10 }}>
                    {rec.official_source_url && (
                      <a
                        href={rec.official_source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-secondary btn-sm"
                      >
                        <ExternalLink size={12} /> Primary Source Registry
                      </a>
                    )}
                    {rec.official_application_url && rec.official_application_url !== rec.official_source_url && (
                      <a
                        href={rec.official_application_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-secondary btn-sm"
                      >
                        <ExternalLink size={12} /> Application Portal
                      </a>
                    )}
                  </div>

                  <button
                    type="button"
                    className={`btn btn-sm ${isClosed ? "btn-secondary" : ""}`}
                    onClick={() => handleStartApp(rec.opportunity_id)}
                  >
                    {isClosed ? "Track in Workspace" : "Prepare Application"} <ArrowRight size={13} />
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
