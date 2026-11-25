import React, { useEffect, useState } from "react";
import {
  Users,
  FolderKanban,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Plus,
  ShieldCheck,
  Settings,
  BarChart3,
  ArrowRight,
  Clock,
  Lock,
} from "lucide-react";
import { MetricCard, StatusBadge } from "../components/ui/DesignSystem";
import { apiFetch } from "../lib/api";

interface AdminDashboardPageProps {
  onNavigate: (route: string) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<"dashboard" | "verification" | "analytics" | "users" | "settings">("dashboard");

  // Telemetry state
  const [telemetry, setTelemetry] = useState<any>(null);
  const [timeRange, setTimeRange] = useState<"7D" | "30D" | "90D" | "1Y">("30D");

  // Verification center state (Screen 8)
  const [verificationFilter, setVerificationFilter] = useState<"pending" | "approved" | "rejected">("pending");
  const [verificationItems, setVerificationItems] = useState([
    { id: "v1", name: "John Doe", org: "Tech Solutions Ltd", status: "pending", initials: "JD" },
    { id: "v2", name: "Alice Smith", org: "Growth Co Africa", status: "pending", initials: "AS" },
    { id: "v3", name: "Michael King", org: "Innovation Ltd", status: "pending", initials: "MK" },
    { id: "v4", name: "Babatunde Adeleke", org: "AgriScale Hub", status: "approved", initials: "BA" },
    { id: "v5", name: "Chidinma Okoro", org: "Fintech Logistics", status: "approved", initials: "CO" },
  ]);

  // System settings state (Screen 11)
  const [settingsTab, setSettingsTab] = useState<"general" | "security" | "notifications" | "integrations">("general");
  const [platformName, setPlatformName] = useState("CARAVAN");
  const [supportEmail, setSupportEmail] = useState("support@caravan.ng");
  const [savedSettingsMsg, setSavedSettingsMsg] = useState("");

  useEffect(() => {
    // Attempt to load live opportunities & applications to populate admin telemetry
    Promise.all([
      apiFetch<any>("/api/v1/opportunities?limit=10").catch(() => null),
      apiFetch<any>("/api/v1/applications").catch(() => null),
    ]).then(([oppRes, appRes]) => {
      setTelemetry({
        opportunities: oppRes?.opportunities || [],
        applications: appRes?.applications || [],
        totalUsers: 1248,
        totalApplications: 843,
        totalFunded: "$2.5M",
        successRate: "98%",
      });
    });
  }, []);

  const handleApprove = (id: string) => {
    setVerificationItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: "approved" } : item))
    );
  };

  const handleReject = (id: string) => {
    setVerificationItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: "rejected" } : item))
    );
  };

  const pendingCount = verificationItems.filter((v) => v.status === "pending").length;

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Admin Top Navigation Tabs */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: "#FFFFFF" }}>
              Admin Operations Portal
            </h1>
            <span className="pill pill-gold">RBAC Enforced</span>
          </div>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            System overview, applicant verification, analytics telemetry, and configuration.
          </p>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            className={`tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "verification" ? "active" : ""}`}
            onClick={() => setActiveTab("verification")}
          >
            Verification Centre ({pendingCount})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => setActiveTab("analytics")}
          >
            Analytics
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "users" ? "active" : ""}`}
            onClick={() => setActiveTab("users")}
          >
            Users
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            Settings
          </button>
        </div>
      </div>

      {/* 1. ADMIN DASHBOARD VIEW (Screen 7 in Reference) */}
      {activeTab === "dashboard" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* 4 Metric Cards */}
          <div className="grid-4" style={{ gap: 16 }}>
            <MetricCard
              label="Total Users"
              value="1,248"
              sub="Registered ventures"
              tone="default"
              icon={<Users size={18} />}
            />
            <MetricCard
              label="Total Applications"
              value="843"
              sub="Pipelines tracked"
              tone="gold"
              icon={<FolderKanban size={18} />}
            />
            <MetricCard
              label="Total Funded"
              value="$2.5M"
              sub="Disbursed capital"
              tone="default"
              icon={<DollarSign size={18} />}
            />
            <MetricCard
              label="Success Rate"
              value="98%"
              sub="Verified compliance"
              tone="success"
              icon={<TrendingUp size={18} />}
            />
          </div>

          {/* Recent Applications Table (Screen 7) */}
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="row-between">
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700 }}>Recent Applications</h2>
                <p className="muted" style={{ fontSize: 12 }}>Latest pipeline submissions across all registered organizations.</p>
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

            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Requested Capital</th>
                    <th>Status</th>
                    <th>Submitted</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="mono gold-text font-bold">#CAR-2024-004</td>
                    <td className="mono">$75,000</td>
                    <td><StatusBadge status="PENDING" /></td>
                    <td className="muted mono">2m ago</td>
                    <td>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveTab("verification")}>
                        Review
                      </button>
                    </td>
                  </tr>
                  <tr>
                    <td className="mono gold-text font-bold">#CAR-2024-003</td>
                    <td className="mono">$250,000</td>
                    <td><StatusBadge status="APPROVED" /></td>
                    <td className="muted mono">5m ago</td>
                    <td>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveTab("verification")}>
                        Inspect
                      </button>
                    </td>
                  </tr>
                  <tr>
                    <td className="mono gold-text font-bold">#CAR-2024-002</td>
                    <td className="mono">$100,000</td>
                    <td><StatusBadge status="UNDER_REVIEW" /></td>
                    <td className="muted mono">10m ago</td>
                    <td>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveTab("verification")}>
                        Review
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. VERIFICATION CENTRE (Screen 8 in Reference) */}
      {activeTab === "verification" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="row-between" style={{ flexWrap: "wrap", gap: 12 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>Verification Centre</h2>
              <p className="muted" style={{ fontSize: 13 }}>Verify and approve registered applicant ventures and documents.</p>
            </div>

            {/* Filter Tabs: Pending (24), Approved, Rejected */}
            <div className="row" style={{ gap: 8 }}>
              <button
                type="button"
                className={`tab-btn ${verificationFilter === "pending" ? "active" : ""}`}
                onClick={() => setVerificationFilter("pending")}
              >
                Pending ({pendingCount})
              </button>
              <button
                type="button"
                className={`tab-btn ${verificationFilter === "approved" ? "active" : ""}`}
                onClick={() => setVerificationFilter("approved")}
              >
                Approved
              </button>
              <button
                type="button"
                className={`tab-btn ${verificationFilter === "rejected" ? "active" : ""}`}
                onClick={() => setVerificationFilter("rejected")}
              >
                Rejected
              </button>
            </div>
          </div>

          {/* List of Applicants (Screen 8) */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {verificationItems
              .filter((item) => item.status === verificationFilter)
              .map((applicant) => (
                <div
                  key={applicant.id}
                  className="card"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "16px 20px",
                    backgroundColor: "var(--bg-card)",
                    flexWrap: "wrap",
                    gap: 14,
                  }}
                >
                  <div className="row" style={{ gap: 14 }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: "var(--radius-full)",
                        backgroundColor: "var(--bg-secondary)",
                        border: "1px solid var(--border-gold)",
                        color: "var(--accent-gold-bright)",
                        fontWeight: 700,
                        fontSize: 13,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {applicant.initials}
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700 }}>{applicant.name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>Business: {applicant.org}</div>
                    </div>
                  </div>

                  <div className="row" style={{ gap: 10 }}>
                    {applicant.status === "pending" ? (
                      <>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => handleApprove(applicant.id)}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleReject(applicant.id)}
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <StatusBadge status={applicant.status.toUpperCase()} />
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 3. ANALYTICS DASHBOARD (Screen 9 in Reference) */}
      {activeTab === "analytics" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Header & Time Filter */}
          <div className="row-between" style={{ flexWrap: "wrap", gap: 12 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>Analytics Dashboard</h2>
              <p className="muted" style={{ fontSize: 13 }}>Insights and performance metrics across the capital platform.</p>
            </div>

            <div className="row" style={{ gap: 6, backgroundColor: "var(--bg-secondary)", padding: 4, borderRadius: "var(--radius-sm)" }}>
              {(["7D", "30D", "90D", "1Y"] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  className={`btn btn-sm ${timeRange === r ? "btn" : "btn-secondary"}`}
                  style={{ padding: "6px 12px", minWidth: 44 }}
                  onClick={() => setTimeRange(r)}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* 3 Key Metrics with Percentage Change */}
          <div className="grid-3" style={{ gap: 16 }}>
            <MetricCard
              label="Total Applications"
              value="843"
              tone="default"
              delta={{ value: "12%", isPositive: true }}
            />
            <MetricCard
              label="Funding Disbursed"
              value="$2.5M"
              tone="gold"
              delta={{ value: "18%", isPositive: true }}
            />
            <MetricCard
              label="Success Rate"
              value="98%"
              tone="success"
              delta={{ value: "2%", isPositive: true }}
            />
          </div>

          {/* Sharp Gold Line Chart on Dark Grid (Screen 9 in Reference) */}
          <div className="card" style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="row-between">
              <span style={{ fontSize: 14, fontWeight: 700 }}>Capital Pipeline Trajectory ({timeRange})</span>
              <span className="mono gold-text" style={{ fontSize: 12 }}>Peak: $2,500,000</span>
            </div>

            <div style={{ width: "100%", height: 260, position: "relative" }}>
              <svg width="100%" height="100%" viewBox="0 0 800 240" preserveAspectRatio="none">
                {/* Horizontal Grid lines */}
                <line x1="40" y1="30" x2="780" y2="30" stroke="#1F1F1F" strokeDasharray="4 4" />
                <line x1="40" y1="80" x2="780" y2="80" stroke="#1F1F1F" strokeDasharray="4 4" />
                <line x1="40" y1="130" x2="780" y2="130" stroke="#1F1F1F" strokeDasharray="4 4" />
                <line x1="40" y1="180" x2="780" y2="180" stroke="#1F1F1F" strokeDasharray="4 4" />
                <line x1="40" y1="220" x2="780" y2="220" stroke="#2B2B2B" />

                {/* Y Axis labels */}
                <text x="10" y="34" fill="#666666" fontSize="10" fontFamily="monospace">$2.5M</text>
                <text x="10" y="84" fill="#666666" fontSize="10" fontFamily="monospace">$1.8M</text>
                <text x="10" y="134" fill="#666666" fontSize="10" fontFamily="monospace">$1.0M</text>
                <text x="10" y="184" fill="#666666" fontSize="10" fontFamily="monospace">$300K</text>
                <text x="10" y="224" fill="#666666" fontSize="10" fontFamily="monospace">$0</text>

                {/* Sharp Gold Line Polyline */}
                <polyline
                  fill="none"
                  stroke="#C69D49"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points="60,200 150,185 240,195 330,160 420,135 510,140 600,105 690,75 760,40"
                />

                {/* Data Points on Polyline */}
                {[
                  [60, 200],
                  [150, 185],
                  [240, 195],
                  [330, 160],
                  [420, 135],
                  [510, 140],
                  [600, 105],
                  [690, 75],
                  [760, 40],
                ].map(([cx, cy], i) => (
                  <circle
                    key={i}
                    cx={cx}
                    cy={cy}
                    r="4"
                    fill="#C69D49"
                    stroke="#050505"
                    strokeWidth="2"
                  />
                ))}
              </svg>
            </div>
          </div>
        </div>
      )}

      {/* 4. USER MANAGEMENT (Screen 10 in Reference) */}
      {activeTab === "users" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="row-between" style={{ flexWrap: "wrap", gap: 12 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>User Management</h2>
              <p className="muted" style={{ fontSize: 13 }}>Manage platform users, customer organizations, and role permissions.</p>
            </div>
            <button type="button" className="btn btn-sm">
              <Plus size={14} /> Add User
            </button>
          </div>

          {/* Search & Filter */}
          <div className="row" style={{ gap: 10 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <Search size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
              <input className="input" style={{ paddingLeft: 36 }} placeholder="Search users by name or email..." />
            </div>
            <button type="button" className="btn btn-secondary">
              <Filter size={14} /> Filter
            </button>
          </div>

          {/* User Table (Screen 10) */}
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>John Doe</strong></td>
                  <td className="muted mono">john@company.com</td>
                  <td><span className="pill">Customer</span></td>
                  <td><StatusBadge status="ACTIVE" /></td>
                  <td><button type="button" className="btn btn-secondary btn-sm">Edit</button></td>
                </tr>
                <tr>
                  <td><strong>Alice Smith</strong></td>
                  <td className="muted mono">alice@company.com</td>
                  <td><span className="pill">Customer</span></td>
                  <td><StatusBadge status="ACTIVE" /></td>
                  <td><button type="button" className="btn btn-secondary btn-sm">Edit</button></td>
                </tr>
                <tr>
                  <td><strong>Michael King</strong></td>
                  <td className="muted mono">michael@company.com</td>
                  <td><span className="pill pill-gold">Admin</span></td>
                  <td><StatusBadge status="ACTIVE" /></td>
                  <td><button type="button" className="btn btn-secondary btn-sm">Edit</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 5. SYSTEM SETTINGS (Screen 11 in Reference) */}
      {activeTab === "settings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 780 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>System Settings</h2>
            <p className="muted" style={{ fontSize: 13 }}>Configure platform settings, S2S bridge, and notification webhooks.</p>
          </div>

          {/* Tabs: General, Security, Notifications, Integrations */}
          <div className="row" style={{ gap: 8, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 10 }}>
            {(["general", "security", "notifications", "integrations"] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`tab-btn ${settingsTab === t ? "active" : ""}`}
                onClick={() => setSettingsTab(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {savedSettingsMsg && (
            <div className="pill pill-emerald">{savedSettingsMsg}</div>
          )}

          <form
            className="card"
            style={{ display: "flex", flexDirection: "column", gap: 16 }}
            onSubmit={(e) => {
              e.preventDefault();
              setSavedSettingsMsg("System settings updated successfully.");
              setTimeout(() => setSavedSettingsMsg(""), 3000);
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Platform Name</label>
              <input
                className="input"
                value={platformName}
                onChange={(e) => setPlatformName(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">Support Email</label>
              <input
                className="input"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label className="form-label">S2S Bridge Security Status</label>
              <div className="card" style={{ backgroundColor: "var(--bg-secondary)", display: "flex", flexDirection: "column", gap: 6 }}>
                <span className="gold-text mono" style={{ fontSize: 12 }}>X-Ultron-Bridge-Key: Active (HMAC Enforced)</span>
                <span className="muted" style={{ fontSize: 11 }}>Permits authenticated operational telemetry sync with ULTRON host OS.</span>
              </div>
            </div>

            <button
              type="submit"
              className="btn"
              style={{ alignSelf: "flex-start", marginTop: 8 }}
            >
              Save Changes
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
