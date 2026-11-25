import React, { useEffect, useState } from "react";
import {
  Globe,
  FolderKanban,
  CheckCircle2,
  DollarSign,
  ArrowRight,
  Clock,
  Sparkles,
  Compass,
  FileCheck,
  Plus,
  Bookmark,
  ShieldCheck,
  Award,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { apiFetch } from "../lib/api";
import { MetricCard, StatusBadge, EmptyState } from "../components/ui/DesignSystem";
import { FundingOpportunity, Application } from "../types";

interface DashboardPageProps {
  onNavigate: (route: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [opportunities, setOpportunities] = useState<FundingOpportunity[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [totalOppsCount, setTotalOppsCount] = useState<number>(0);
  const [savedCount, setSavedCount] = useState<number>(0);
  const [strongMatchesCount, setStrongMatchesCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      try {
        const [oppRes, appRes, savedRes, eligRes] = await Promise.all([
          apiFetch<any>("/api/v1/opportunities?limit=8"),
          apiFetch<any>("/api/v1/applications").catch(() => ({ applications: [] })),
          apiFetch<any>("/api/v1/saved").catch(() => ({ total: 0, saved: [] })),
          apiFetch<any>("/api/v1/eligibility/recommendations?limit=20").catch(() => ({ total_strong: 0, strong_matches: [] })),
        ]);
        const opps = oppRes.opportunities || [];
        setOpportunities(opps);
        setTotalOppsCount(oppRes.total ?? opps.length);
        setApplications(appRes.applications || []);
        setSavedCount(savedRes.total ?? (savedRes.saved || []).length);
        setStrongMatchesCount(eligRes.total_strong ?? (eligRes.strong_matches || []).length);
      } catch {
        // keep honest zero states
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const totalApps = applications.length;
  const inProgressApps = applications.filter((a) => a.status === "DRAFTING" || a.status === "DOCS_COLLECTING" || a.status === "REVIEW").length;
  const submittedApps = applications.filter((a) => a.status === "SUBMITTED").length;
  const awardedApps = applications.filter((a) => a.status === "AWARDED").length;

  const successRateDisplay =
    totalApps === 0
      ? "N/A"
      : submittedApps + awardedApps === 0
      ? "0%"
      : `${Math.round((awardedApps / (submittedApps + awardedApps)) * 100)}%`;

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Welcome Header */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "#FFFFFF" }}>
            Welcome back, {user?.full_name || "Applicant"}
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            {user?.organization_name ? `Operating as ${user.organization_name}` : "Verified Venture Funding Portal"}
          </p>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => onNavigate("eligibility")}
          >
            <Sparkles size={14} color="var(--accent-gold-bright)" /> Eligibility Scorecard
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate("marketplace")}
          >
            <Compass size={14} /> Browse All ({totalOppsCount})
          </button>
        </div>
      </div>

      {/* 4 Metric Cards (Calculated directly from real database state) */}
      <div className="grid-4" style={{ gap: 16 }}>
        <MetricCard
          label="Available Opportunities"
          value={totalOppsCount}
          sub="Verified institutional programs"
          tone="default"
          icon={<Globe size={18} />}
        />
        <MetricCard
          label="Active Applications"
          value={totalApps}
          sub={totalApps === 0 ? "No active applications yet" : `${inProgressApps} drafting, ${submittedApps} submitted`}
          tone="gold"
          icon={<FolderKanban size={18} />}
        />
        <MetricCard
          label="Qualified Matches"
          value={strongMatchesCount}
          sub="Strong criteria fit"
          tone="success"
          icon={<CheckCircle2 size={18} />}
        />
        <MetricCard
          label="Saved Opportunities"
          value={savedCount}
          sub="Bookmarked in pipeline"
          tone="default"
          icon={<Bookmark size={18} />}
        />
      </div>

      {/* Main Workspace Layout */}
      <div className="grid-2" style={{ gap: 24, alignItems: "start" }}>
        {/* Left Column: Recent Applications or Application Initiation */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="row-between">
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>My Application Workspace</h2>
            <button
              type="button"
              className="gold-text"
              style={{ fontSize: 12, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4 }}
              onClick={() => onNavigate("applications")}
            >
              Open workspace <ArrowRight size={13} />
            </button>
          </div>

          {loading ? (
            <div className="muted" style={{ padding: 24, textAlign: "center" }}>
              Loading applications...
            </div>
          ) : applications.length === 0 ? (
            <div
              style={{
                backgroundColor: "var(--bg-secondary)",
                padding: 24,
                borderRadius: "var(--radius-sm)",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                alignItems: "center",
              }}
            >
              <FolderKanban size={32} color="var(--accent-gold)" />
              <div>
                <strong style={{ fontSize: 14 }}>No applications in progress</strong>
                <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Browse verified opportunities to start an application with structured checklists and document verification.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => onNavigate("marketplace")}
              >
                Find Opportunities
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {applications.slice(0, 4).map((app) => (
                <div
                  key={app.application_id}
                  className="row-between"
                  style={{
                    padding: "12px 14px",
                    backgroundColor: "var(--bg-secondary)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: 13, color: "#FFFFFF" }}>{app.opportunity_title}</strong>
                    <div className="muted" style={{ fontSize: 11 }}>{app.provider}</div>
                  </div>
                  <StatusBadge status={app.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Verified Funding Facilities */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="row-between">
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>Verified Funding Facilities</h2>
            <button
              type="button"
              className="gold-text"
              style={{ fontSize: 12, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4 }}
              onClick={() => onNavigate("marketplace")}
            >
              Explore all ({totalOppsCount}) <ArrowRight size={13} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {opportunities.slice(0, 4).map((opp) => (
              <div
                key={opp.opportunity_id}
                className="row-between"
                style={{
                  padding: "12px 14px",
                  backgroundColor: "var(--bg-secondary)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                  alignItems: "center",
                }}
              >
                <div style={{ flex: "1 1 200px" }}>
                  <strong style={{ fontSize: 13, color: "#FFFFFF" }}>{opp.title}</strong>
                  <div className="muted" style={{ fontSize: 11 }}>
                    {opp.provider} · <span className="gold-text mono">{opp.amount_display}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onNavigate("marketplace")}
                >
                  View
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
