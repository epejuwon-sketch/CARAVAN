import React, { useEffect, useState } from "react";
import { HelpCircle, MessageSquare, Send, CheckCircle2 } from "lucide-react";
import { apiFetch } from "../lib/api";
import { StatusBadge } from "../components/ui/DesignSystem";

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
      loadTickets();
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24, maxWidth: 840 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 800 }}>Institutional Support &amp; Help Desk</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Submit inquiries regarding grantmaker verification, application guidelines, or billing.
        </p>
      </div>

      {msg && <div className="pill pill-cyan">{msg}</div>}

      <form onSubmit={handleCreateTicket} className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <strong style={{ fontSize: 14 }}>Create Support Ticket</strong>
        <input
          className="input"
          placeholder="Inquiry Subject (e.g. Question on BOI Loan moratorum requirements)"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          required
        />
        <textarea
          className="input"
          rows={4}
          placeholder="Detailed description of your question or issue..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
        />
        <button type="submit" className="btn btn-sm" style={{ alignSelf: "flex-start" }}>
          <Send size={13} /> Submit Ticket
        </button>
      </form>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <strong style={{ fontSize: 15 }}>Ticket History ({tickets.length})</strong>
        {loading ? (
          <div className="card muted" style={{ textAlign: "center", padding: 24 }}>Loading tickets...</div>
        ) : tickets.length === 0 ? (
          <div className="card muted" style={{ textAlign: "center", padding: 24 }}>No previous support tickets.</div>
        ) : (
          tickets.map((t) => (
            <div key={t.ticket_id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="row-between">
                <strong style={{ fontSize: 14 }}>{t.subject}</strong>
                <StatusBadge status={t.status} />
              </div>
              <p className="muted" style={{ fontSize: 13 }}>{t.message}</p>
              {t.response && (
                <div style={{ padding: 10, backgroundColor: "var(--bg-secondary)", borderRadius: "var(--radius-sm)", borderLeft: "3px solid var(--accent-cyan)", fontSize: 12 }}>
                  <strong>CARAVAN Operations Response:</strong> {t.response}
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
