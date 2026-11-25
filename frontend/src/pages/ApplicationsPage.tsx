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
} from "lucide-react";
import { Application } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge, Drawer } from "../components/ui/DesignSystem";

interface ApplicationsPageProps {
  onNavigate: (route: string) => void;
}

export const ApplicationsPage: React.FC<ApplicationsPageProps> = ({ onNavigate }) => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [docName, setDocName] = useState("");
  const [docType, setDocType] = useState("PITCH_DECK");
  const [msg, setMsg] = useState("");

  async function loadApplications() {
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/applications");
      setApplications(res.applications || []);
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
      setSelectedApp((prev) => prev ? { ...prev, checklist_progress: res.checklist_progress } : null);
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
      setSelectedApp((prev) => prev ? { ...prev, status: res.status } : null);
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
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800 }}>Application Workspace &amp; Pipelines</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Organize requirements checklists, track deliverables, and manage submission milestones.
          </p>
        </div>
        <button type="button" className="btn btn-sm" onClick={() => onNavigate("discover")}>
          <Plus size={13} /> Discover Capital to Apply
        </button>
      </div>

      {msg && <div className="pill pill-cyan">{msg}</div>}

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading your application workspaces...
        </div>
      ) : applications.length === 0 ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <FolderKanban size={32} />
          <strong>No active application pipelines.</strong>
          <p style={{ maxWidth: 440, fontSize: 13 }}>
            Find a verified funding opportunity on the Marketplace and initialize your application workspace.
          </p>
          <button type="button" className="btn btn-sm" onClick={() => onNavigate("discover")}>
            Browse Funding Directory
          </button>
        </div>
      ) : (
        <div className="grid-2" style={{ gap: 16 }}>
          {applications.map((app) => {
            const totalItems = app.checklist_progress.length;
            const completedItems = app.checklist_progress.filter((c) => c.completed).length;
            const progressPct = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

            return (
              <div
                key={app.application_id}
                className="card card-interactive"
                style={{ display: "flex", flexDirection: "column", gap: 14 }}
                onClick={() => setSelectedApp(app)}
              >
                <div className="row-between">
                  <span className="pill pill-cyan">{app.funding_type}</span>
                  <StatusBadge status={app.status} />
                </div>

                <div>
                  <strong style={{ fontSize: 16 }}>{app.opportunity_title}</strong>
                  <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{app.provider}</div>
                </div>

                {app.deadline_at && (
                  <div className="row muted" style={{ gap: 4, fontSize: 12 }}>
                    <Clock size={12} /> Deadline: {new Date(app.deadline_at).toLocaleDateString()}
                  </div>
                )}

                {/* Progress bar */}
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <div className="row-between" style={{ fontSize: 11 }}>
                    <span className="muted">Checklist Completion</span>
                    <span className="mono">{completedItems}/{totalItems} ({progressPct}%)</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, backgroundColor: "var(--bg-secondary)", overflow: "hidden" }}>
                    <div style={{ width: `${progressPct}%`, height: "100%", backgroundColor: "var(--accent-emerald)", transition: "width 0.2s" }} />
                  </div>
                </div>

                <div className="row-between" style={{ marginTop: 4 }}>
                  <span className="muted" style={{ fontSize: 11 }}>Updated: {new Date(app.updated_at).toLocaleDateString()}</span>
                  <button type="button" className="btn btn-secondary btn-sm">
                    Open Workspace <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Application Detail Drawer */}
      <Drawer
        open={Boolean(selectedApp)}
        title={selectedApp?.opportunity_title || "Application Workspace"}
        onClose={() => setSelectedApp(null)}
      >
        {selectedApp && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, fontSize: 13 }}>
            <div className="row-between">
              <span className="pill pill-cyan">{selectedApp.funding_type}</span>
              <select
                className="input"
                style={{ width: "auto" }}
                value={selectedApp.status}
                onChange={(e) => handleUpdateStatus(selectedApp.application_id, e.target.value)}
              >
                <option value="DRAFTING">DRAFTING</option>
                <option value="DOCS_COLLECTING">DOCS_COLLECTING</option>
                <option value="REVIEW">REVIEW</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="AWARDED">AWARDED</option>
                <option value="REJECTED">REJECTED</option>
              </select>
            </div>

            {/* Checklist */}
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <strong style={{ fontSize: 13 }}>Requirements Checklist</strong>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedApp.checklist_progress.map((item, idx) => (
                  <label key={idx} className="row" style={{ gap: 8, cursor: "pointer", fontSize: 13 }}>
                    <input
                      type="checkbox"
                      checked={item.completed}
                      onChange={() => handleToggleChecklistItem(selectedApp.application_id, idx)}
                    />
                    <span style={{ textDecoration: item.completed ? "line-through" : "none", color: item.completed ? "var(--text-muted)" : "inherit" }}>
                      {item.item}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Document Manager */}
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <strong style={{ fontSize: 13 }}>Attach Supporting Documents</strong>
              <div className="row" style={{ gap: 8 }}>
                <input
                  className="input"
                  placeholder="Document filename (e.g. Pitch_Deck_2026.pdf)"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                />
                <select
                  className="input"
                  style={{ width: 140 }}
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  <option value="PITCH_DECK">Pitch Deck</option>
                  <option value="FINANCIALS">Financials</option>
                  <option value="CAC_CERT">CAC Certificate</option>
                  <option value="TAX_CLEARANCE">Tax Clearance</option>
                </select>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => handleAddDocument(selectedApp.application_id)}
                >
                  <Upload size={12} /> Add
                </button>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
