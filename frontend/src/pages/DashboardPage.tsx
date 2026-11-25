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
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      try {
        const [oppRes, appRes, savedRes] = await Promise.all([
          apiFetch<any>("/api/v1/opportunities?limit=10"),
          apiFetch<any>("/api/v1/applications"),
          apiFetch<any>("/api/v1/saved").catch(() => ({ total: 0 })),
        ]);
        const opps = oppRes.opportunities || [];
        setOpportunities(opps);
        setTotalOppsCount(oppRes.total ?? opps.length);
        setApplications(appRes.applications || []);
        setSavedCount(savedRes.total || (savedRes.saved || []).length || 0);
      } catch {
        // fallback
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const totalApps = applications.length;
  const approvedCount = applications.filter((a) => a.status === "AWARDED" || a.status === "SUBMITTED").length;
  const successRate = totalApps > 0 ? `${Math.round((approvedCount / totalApps) * 100)}%` : "—";
  const successSub = totalApps > 0 ? `${approvedCount} in active review` : "No submissions yet";
  const fundedValue = totalApps > 0 ? "—" : "$0";
  const fundedSub = totalApps > 0 ? "Awaiting disbursement review" : "No active disbursements";

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Welcome Header */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            Welcome back, {user?.full_name || "Enterprise User"}
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Here's your funding overview and capital pipeline telemetry.
          </p>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => onNavigate("discover")}
          >
            <Compass size={14} /> Find Funding
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate("applications")}
          >
            <Plus size={14} /> New Application
          </button>
        </div>
      </div>

      {/* 4 Metric Cards (Screen 2 in Reference) */}
      <div className="grid-4" style={{ gap: 16 }}>
        <MetricCard
          label="Available Opportunities"
          value={totalOppsCount}
          sub="Institutional programs"
          tone="default"
          icon={<Globe size={18} />}
        />
        <MetricCard
          label="My Applications"
          value={totalApps}
          sub={totalApps > 0 ? `${approvedCount} active in pipeline` : "0 in pipeline"}
          tone="gold"
          icon={<FolderKanban size={18} />}
        />
        <MetricCard
          label="Success Rate"
          value={successRate}
          sub={successSub}
          tone="success"
          icon={<CheckCircle2 size={18} />}
        />
        <MetricCard
          label="Total Funded"
          value={fundedValue}
          sub={fundedSub}
          tone="default"
          icon={<DollarSign size={18} />}
        />
      </div>

      {/* Recent Activity Card (Screen 2 in Reference) */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div className="row-between">
          <div className="row" style={{ gap: 8 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>Recent Activity</h2>
            <span className="pill pill-gold">{applications.length} updates</span>
          </div>
          <button
            type="button"
            className="gold-text"
            style={{ fontSize: 12, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4 }}
            onClick={() => onNavigate("applications")}
          >
            View all <ArrowRight size={13} />
          </button>
        </div>

        {applications.length === 0 ? (
          <EmptyState
            icon={<Clock size={28} />}
            title="No recent activity"
            description="Operational activity will be tracked here when you initiate or update funding applications."
            actionLabel="Find Opportunities"
            onAction={() => onNavigate("discover")}
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {applications.slice(0, 5).map((app) => (
              <div
                key={app.application_id}
                className="row-between"
                style={{
                  padding: "12px 16px",
                  backgroundColor: "var(--bg-secondary)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                  flexWrap: "wrap",
                  gap: 10,
                }}
              >
                <div className="row" style={{ gap: 12 }}>
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "var(--radius-full)",
                      backgroundColor: "var(--status-info-bg)",
                      color: "var(--status-info-text)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Clock size={16} />
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>
                      Application {app.status.replace(/_/g, " ")}
                    </div>
                    <div className="muted" style={{ fontSize: 11 }}>
                      {app.opportunity_title} · {app.provider}
                    </div>
                  </div>
                </div>
                <div className="row" style={{ gap: 10 }}>
                  <StatusBadge status={app.status} />
                  <span className="mono muted" style={{ fontSize: 11 }}>
                    {new Date(app.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Featured Verified Opportunities */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="row-between">
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>Recommended Opportunities</h2>
            <p className="muted" style={{ fontSize: 12 }}>Curated institutional capital facilities matching your venture profile.</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate("discover")}
          >
            Explore All ({totalOppsCount})
          </button>
        </div>

        {opportunities.length === 0 ? (
          <EmptyState
            icon={<Sparkles size={28} />}
            title="No opportunities loaded"
            description="Verified capital programs will appear here."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {opportunities.slice(0, 3).map((opp) => (
              <div
                key={opp.opportunity_id}
                className="card"
                style={{
                  backgroundColor: "var(--bg-secondary)",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 14,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: "var(--radius-sm)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-gold)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--accent-gold-bright)",
                      flexShrink: 0,
                    }}
                  >
                    <Sparkles size={18} />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>{opp.title}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {opp.provider} · <span className="gold-text">{opp.amount_display}</span>
                    </div>
                  </div>
                </div>

                <div className="row" style={{ gap: 10 }}>
                  <StatusBadge status={opp.verification_status} />
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => onNavigate("discover")}
                  >
                    Apply Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
