import React, { useEffect, useState } from "react";
import { HelpCircle, MessageSquare, Send, CheckCircle2 } from "lucide-react";
import { apiFetch } from "../lib/api";
import { StatusBadge, EmptyState } from "../components/ui/DesignSystem";

export const SupportPage: React.FC = () => {
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [msg, setMsg] = useState("");

  async function loadTickets() {
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/support/tickets");
      setTickets(res.tickets || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTickets();
  }, []);

  async function handleCreateTicket(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;
    try {
      await apiFetch("/api/v1/support/tickets", {
        method: "POST",
        body: JSON.stringify({ subject: subject.trim(), message: message.trim() }),
      });
      setSubject("");
      setMessage("");
      setMsg("Support ticket submitted. Our operations team will respond promptly.");
      setTimeout(() => setMsg(""), 5000);
      loadTickets();
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 28, maxWidth: 840 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
          Help &amp; Support Desk
        </h1>
        <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
          Submit inquiries regarding program verification, statutory guidelines, or platform access.
        </p>
      </div>

      {msg && <div className="pill pill-emerald" style={{ padding: "8px 14px" }}>{msg}</div>}

      {/* Ticket Creation Form */}
      <form onSubmit={handleCreateTicket} className="card card-gold" style={{ display: "flex", flexDirection: "column", gap: 16, backgroundColor: "var(--bg-secondary)" }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Submit an Inquiry</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label className="form-label">Subject *</label>
          <input
            className="input"
            placeholder="e.g. Inquiries regarding BOI Loan moratorium requirements"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label className="form-label">Message Details *</label>
          <textarea
            className="input"
            rows={4}
            placeholder="Detailed description of your question or compliance clarification..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="btn btn-sm" style={{ alignSelf: "flex-start", marginTop: 4 }}>
          <Send size={13} /> Submit Ticket
        </button>
      </form>

      {/* Ticket History */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Ticket History ({tickets.length})</h2>
        {loading ? (
          <div className="card muted" style={{ textAlign: "center", padding: 32 }}>Loading tickets...</div>
        ) : tickets.length === 0 ? (
          <EmptyState
            icon={<HelpCircle size={32} />}
            title="No support tickets"
            description="You have no active or historical support tickets. Our institutional support team is available whenever you need assistance."
          />
        ) : (
          tickets.map((t) => (
            <div key={t.ticket_id} className="card" style={{ display: "flex", flexDirection: "column", gap: 10, backgroundColor: "var(--bg-card)" }}>
              <div className="row-between">
                <strong style={{ fontSize: 14, color: "#FFFFFF" }}>{t.subject}</strong>
                <StatusBadge status={t.status} />
              </div>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.5 }}>{t.message}</p>
              {t.response && (
                <div style={{ padding: "12px 14px", backgroundColor: "var(--bg-secondary)", borderRadius: "var(--radius-sm)", borderLeft: "3px solid var(--accent-gold)", fontSize: 12 }}>
                  <strong className="gold-text">CARAVAN Operations Response:</strong> {t.response}
                </div>
              )}
              <span className="muted mono" style={{ fontSize: 11 }}>Created: {new Date(t.created_at).toLocaleString()}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
