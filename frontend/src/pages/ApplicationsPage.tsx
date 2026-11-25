import React, { useEffect, useState } from "react";
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  FileText,
  Upload,
  Plus,
  RefreshCw,
  ArrowRight,
  ArrowLeft,
  X,
  FileCheck,
  ShieldCheck,
  DollarSign,
  Building2,
} from "lucide-react";
import { Application, FundingOpportunity } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge, Drawer, Stepper, EmptyState } from "../components/ui/DesignSystem";

interface ApplicationsPageProps {
  onNavigate: (route: string) => void;
}

export const ApplicationsPage: React.FC<ApplicationsPageProps> = ({ onNavigate }) => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [opportunities, setOpportunities] = useState<FundingOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  // New Application Modal / Stepper State (Screens 4 & 5)
  const [isApplying, setIsApplying] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedOppId, setSelectedOppId] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [businessType, setBusinessType] = useState("Private Limited Company (LTD)");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [amountRequested, setAmountRequested] = useState("$100,000");
  const [purposeOfFunding, setPurposeOfFunding] = useState("Working capital & production expansion");
  const [docName, setDocName] = useState("");
  const [docType, setDocType] = useState("PITCH_DECK");
  const [msg, setMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadApplications() {
    setLoading(true);
    try {
      const [appRes, oppRes] = await Promise.all([
        apiFetch<any>("/api/v1/applications"),
        apiFetch<any>("/api/v1/opportunities?limit=50"),
      ]);
      setApplications(appRes.applications || []);
      setOpportunities(oppRes.opportunities || []);
      if ((oppRes.opportunities || []).length > 0 && !selectedOppId) {
        setSelectedOppId(oppRes.opportunities[0].opportunity_id);
      }
    } catch (err: any) {
      setMsg(err.message || "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApplications();
  }, []);

  async function handleToggleChecklistItem(appId: string, index: number) {
    if (!selectedApp) return;
    const updatedChecklist = selectedApp.checklist_progress.map((item, idx) =>
      idx === index ? { ...item, completed: !item.completed } : item
    );

    try {
      const res = await apiFetch<any>(`/api/v1/applications/${appId}`, {
        method: "PATCH",
        body: JSON.stringify({ checklist_progress: updatedChecklist }),
      });
      setSelectedApp((prev) => (prev ? { ...prev, checklist_progress: res.checklist_progress } : null));
      loadApplications();
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  async function handleUpdateStatus(appId: string, newStatus: string) {
    try {
      const res = await apiFetch<any>(`/api/v1/applications/${appId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      setSelectedApp((prev) => (prev ? { ...prev, status: res.status } : null));
      loadApplications();
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  async function handleAddDocument(appId: string) {
    if (!docName.trim()) return;
    try {
      await apiFetch(`/api/v1/applications/${appId}/documents`, {
        method: "POST",
        body: JSON.stringify({
          name: docName.trim(),
          doc_type: docType,
          file_size_bytes: 2048000,
        }),
      });
      setDocName("");
      setMsg("Document metadata recorded.");
      // Refresh current application workspace
      const updated = await apiFetch<any>(`/api/v1/applications/${appId}`);
      setSelectedApp(updated);
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  // Submit new application through multi-step form (Screens 4 & 5)
  async function handleSubmitNewApplication() {
    setSubmitting(true);
    try {
      const note = `[Application Details] Business: ${businessName} (${businessType}, RC: ${registrationNumber}) | Request: ${amountRequested} for ${purposeOfFunding}`;
      await apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({
          opportunity_id: selectedOppId,
          notes: note,
        }),
      });
      setIsApplying(false);
      setCurrentStep(1);
      setMsg("Application submitted successfully.");
      await loadApplications();
    } catch (err: any) {
      setMsg(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Page Header (Screen 6 in Reference) */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            My Applications
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Track the status of your applications and manage preparation deliverables.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            setIsApplying(true);
            setCurrentStep(1);
          }}
        >
          <Plus size={14} /> Apply for Funding
        </button>
      </div>

      {msg && (
        <div className="pill pill-cyan" style={{ padding: "8px 14px" }}>
          {msg}
        </div>
      )}

      {/* Multi-Step Application Flow Modal (Screens 4 & 5 in Reference) */}
      {isApplying && (
        <div className="card card-gold" style={{ padding: "28px 32px", display: "flex", flexDirection: "column", gap: 20, backgroundColor: "var(--bg-secondary)" }}>
          <div className="row-between">
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>Apply for Funding</h2>
              <p className="muted" style={{ fontSize: 12 }}>Complete the institutional preparation form below.</p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setIsApplying(false)}
            >
              <X size={14} /> Cancel
            </button>
          </div>

          {/* Stepper: Business -> Details -> Documents -> Review */}
          <Stepper
            steps={["Business", "Details", "Documents", "Review"]}
            currentStep={currentStep}
            onStepClick={(step) => setCurrentStep(step)}
          />

          {/* Step 1: Business Information (Screen 4) */}
          {currentStep === 1 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
                Business Information
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label className="form-label">Target Funding Program *</label>
                <select
                  className="input"
                  value={selectedOppId}
                  onChange={(e) => setSelectedOppId(e.target.value)}
                >
                  {opportunities.map((o) => (
                    <option key={o.opportunity_id} value={o.opportunity_id}>
                      {o.title} — {o.provider} ({o.amount_display})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label className="form-label">Business Name *</label>
                <input
                  className="input"
                  placeholder="Enter business name"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  required
                />
              </div>

              <div className="grid-2" style={{ gap: 16 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label className="form-label">Business Type *</label>
                  <select
                    className="input"
                    value={businessType}
                    onChange={(e) => setBusinessType(e.target.value)}
                  >
                    <option value="Private Limited Company (LTD)">Private Limited Company (LTD)</option>
                    <option value="Public Limited Company (PLC)">Public Limited Company (PLC)</option>
                    <option value="Registered Cooperative">Registered Cooperative</option>
                    <option value="Enterprise / Sole Proprietorship">Enterprise / Sole Proprietorship</option>
                  </select>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label className="form-label">Business Registration Number (CAC RC) *</label>
                  <input
                    className="input"
                    placeholder="e.g. RC-1928374"
                    value={registrationNumber}
                    onChange={(e) => setRegistrationNumber(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setCurrentStep(2)}
                >
                  Next Step <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Funding Request & Details (Screen 5) */}
          {currentStep === 2 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
                Funding Request Details
              </h3>

              <div className="grid-2" style={{ gap: 16 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label className="form-label">Amount Requested *</label>
                  <select
                    className="input"
                    value={amountRequested}
                    onChange={(e) => setAmountRequested(e.target.value)}
                  >
                    <option value="$25,000 - $50,000">$25,000 - $50,000</option>
                    <option value="$50,000 - $100,000">$50,000 - $100,000</option>
                    <option value="$100,000 - $250,000">$100,000 - $250,000</option>
                    <option value="$250,000 - $500,000">$250,000 - $500,000</option>
                    <option value="$500,000 - $1,000,000">$500,000 - $1,000,000</option>
                    <option value="$1,000,000+">$1,000,000+</option>
                  </select>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label className="form-label">Deployment Horizon</label>
                  <select className="input">
                    <option value="Immediate (1-3 months)">Immediate (1-3 months)</option>
                    <option value="Near-term (3-6 months)">Near-term (3-6 months)</option>
                    <option value="Strategic (6-12 months)">Strategic (6-12 months)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label className="form-label">Purpose of Funding *</label>
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Describe how the capital will be utilized (e.g. capital expenditure, working capital, market expansion)..."
                  value={purposeOfFunding}
                  onChange={(e) => setPurposeOfFunding(e.target.value)}
                  required
                />
              </div>

              <div className="row-between" style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setCurrentStep(1)}
                >
                  <ArrowLeft size={14} /> Previous
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setCurrentStep(3)}
                >
                  Next Step <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Documents Submission */}
          {currentStep === 3 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
                Document Submission
              </h3>
              <p className="muted" style={{ fontSize: 13 }}>
                Upload or declare mandatory compliance documents for the funding provider.
              </p>

              <div className="grid-3" style={{ gap: 12 }}>
                <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 6 }}>
                  <strong style={{ fontSize: 13 }}>1. Pitch Deck / Business Plan</strong>
                  <span className="pill pill-emerald" style={{ alignSelf: "flex-start" }}>Ready</span>
                </div>
                <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 6 }}>
                  <strong style={{ fontSize: 13 }}>2. CAC Certificate of Inc.</strong>
                  <span className="pill pill-emerald" style={{ alignSelf: "flex-start" }}>Ready</span>
                </div>
                <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 6 }}>
                  <strong style={{ fontSize: 13 }}>3. Audited Financial Statements</strong>
                  <span className="pill pill-gold" style={{ alignSelf: "flex-start" }}>Pending</span>
                </div>
              </div>

              <div className="row-between" style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setCurrentStep(2)}
                >
                  <ArrowLeft size={14} /> Previous
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setCurrentStep(4)}
                >
                  Review Application <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Review & Final Submission */}
          {currentStep === 4 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
                Review Application
              </h3>

              <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
                <div><strong>Business:</strong> {businessName || "Registered Enterprise"} ({businessType}, RC: {registrationNumber || "RC-Pending"})</div>
                <div><strong>Amount Requested:</strong> <span className="gold-text">{amountRequested}</span></div>
                <div><strong>Purpose:</strong> {purposeOfFunding}</div>
                <div><strong>Governance:</strong> AEGIS Zero-Knowledge Verification Enforced</div>
              </div>

              <div className="row-between" style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setCurrentStep(3)}
                >
                  <ArrowLeft size={14} /> Previous
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={submitting}
                  onClick={handleSubmitNewApplication}
                >
                  {submitting ? "Submitting..." : "Submit Application"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Applications List (Matching Screen 6 in Reference) */}
      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 48 }}>
          Loading application pipelines...
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={<FolderKanban size={36} />}
          title="No active funding applications"
          description="You haven't initiated any funding applications yet. Explore verified opportunities to begin matching."
          actionLabel="Explore Opportunities"
          onAction={() => onNavigate("discover")}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {applications.map((app) => {
            const appIdFormatted = `#${app.application_id.toUpperCase()}`;
            return (
              <div
                key={app.application_id}
                className="card"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 16,
                  padding: "18px 24px",
                  backgroundColor: "var(--bg-card)",
                }}
              >
                {/* ID & Opportunity Info */}
                <div style={{ display: "flex", alignItems: "center", gap: 16, flex: "1 1 360px" }}>
                  <div className="mono gold-text" style={{ fontSize: 13, fontWeight: 700 }}>
                    {appIdFormatted}
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                      <strong style={{ fontSize: 15, color: "#FFFFFF" }}>
                        {app.opportunity_title}
                      </strong>
                      <StatusBadge status={app.status} />
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {app.provider} · Created: {new Date(app.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                {/* Right: View Details Action (Screen 6) */}
                <div className="row" style={{ gap: 12 }}>
                  <span className="muted mono" style={{ fontSize: 12 }}>
                    {new Date(app.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </span>
                  <button
                    type="button"
                    className="gold-text"
                    style={{ fontSize: 13, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4 }}
                    onClick={() => setSelectedApp(app)}
                  >
                    View Details <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Application Workspace Drawer */}
      <Drawer
        open={Boolean(selectedApp)}
        title={selectedApp?.opportunity_title || "Application Workspace"}
        onClose={() => setSelectedApp(null)}
      >
        {selectedApp && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="row-between">
              <span className="mono gold-text" style={{ fontSize: 15, fontWeight: 700 }}>
                {selectedApp.provider}
              </span>
              <StatusBadge status={selectedApp.status} />
            </div>

            {/* Checklist Progress */}
            <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="row-between">
                <strong style={{ fontSize: 14 }}>Preparation Deliverables</strong>
                <span className="muted" style={{ fontSize: 12 }}>
                  {(selectedApp.checklist_progress || []).filter((i) => i.completed).length} / {(selectedApp.checklist_progress || []).length} completed
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(selectedApp.checklist_progress || []).map((item, idx) => (
                  <label
                    key={idx}
                    className="row"
                    style={{
                      gap: 10,
                      fontSize: 13,
                      cursor: "pointer",
                      padding: "8px 12px",
                      backgroundColor: "var(--bg-secondary)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={item.completed}
                      onChange={() => handleToggleChecklistItem(selectedApp.application_id, idx)}
                      style={{ accentColor: "var(--accent-gold)" }}
                    />
                    <span style={{ textDecoration: item.completed ? "line-through" : "none", color: item.completed ? "var(--text-muted)" : "var(--text-primary)" }}>
                      {item.item}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Status Transition Control */}
            <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 10 }}>
              <strong style={{ fontSize: 14 }}>Pipeline Milestone Status</strong>
              <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                {["DRAFTING", "DOCS_COLLECTING", "REVIEW", "SUBMITTED"].map((st) => (
                  <button
                    key={st}
                    type="button"
                    className={`btn btn-sm ${selectedApp.status === st ? "btn" : "btn-secondary"}`}
                    onClick={() => handleUpdateStatus(selectedApp.application_id, st)}
                  >
                    {st.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            {/* Attach Document Metadata */}
            <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 12 }}>
              <strong style={{ fontSize: 14 }}>Add Compliance Document</strong>
              <div className="grid-2" style={{ gap: 10 }}>
                <input
                  className="input"
                  placeholder="Document filename (e.g. Audited_Accounts_2025.pdf)"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                />
                <select
                  className="input"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  <option value="PITCH_DECK">Pitch Deck</option>
                  <option value="FINANCIAL_STATEMENTS">Financial Statements</option>
                  <option value="CAC_CERTIFICATE">CAC Certificate</option>
                  <option value="TAX_CLEARANCE">Tax Clearance (TCC)</option>
                  <option value="BUSINESS_PLAN">Business Plan</option>
                </select>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ alignSelf: "flex-start" }}
                onClick={() => handleAddDocument(selectedApp.application_id)}
              >
                <Upload size={13} /> Record Document Attachment
              </button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
