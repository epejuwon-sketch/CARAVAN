import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Send,
  Bot,
  User,
  ShieldCheck,
  ExternalLink,
  PlusCircle,
  FileText,
  Bookmark,
  CheckCircle2,
  AlertCircle,
  FolderKanban,
  Download,
} from "lucide-react";
import { apiFetch } from "../lib/api";

interface CopilotPageProps {
  onNavigate: (route: string) => void;
}

interface Citation {
  opportunity_id: string;
  title: string;
  provider: string;
  funding_type: string;
  amount_display: string;
  official_source_url: string;
  deadline_at: string;
}

interface Action {
  label: string;
  action: string;
  data: any;
}

interface Message {
  message_id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  citations?: Citation[];
  actions?: Action[];
  created_at: string;
}

interface Session {
  session_id: string;
  title: string;
  context_mode: string;
  message_count: number;
  updated_at: string;
}

export const CopilotPage: React.FC<CopilotPageProps> = ({ onNavigate }) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [readiness, setReadiness] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load sessions and readiness on mount
  useEffect(() => {
    loadSessions();
    loadReadiness();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadSessions() {
    try {
      const data = await apiFetch<any>("/api/v1/copilot/sessions");
      const sessList: Session[] = data.sessions || [];
      setSessions(sessList);
      if (sessList.length > 0) {
        selectSession(sessList[0].session_id);
      } else {
        createNewSession();
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load copilot sessions");
    }
  }

  async function loadReadiness() {
    try {
      const rep = await apiFetch<any>("/api/v1/copilot/readiness-report");
      setReadiness(rep.readiness);
    } catch {
      // Ignored if unauthenticated or new
    }
  }

  async function selectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    try {
      const data = await apiFetch<any>(`/api/v1/copilot/sessions/${sessionId}/messages`);
      setMessages(data.messages || []);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load messages");
    }
  }

  async function createNewSession() {
    try {
      const res = await apiFetch<any>("/api/v1/copilot/sessions", {
        method: "POST",
        body: JSON.stringify({ title: "New Funding Consultation" }),
      });
      const newSess: Session = {
        session_id: res.session_id,
        title: res.title,
        context_mode: res.context_mode,
        message_count: 0,
        updated_at: new Date().toISOString(),
      };
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(res.session_id);
      setMessages([]);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start session");
    }
  }

  async function handleSendMessage(promptText?: string) {
    const textToSend = promptText || inputPrompt;
    if (!textToSend.trim() || !activeSessionId || loading) return;

    setInputPrompt("");
    setLoading(true);
    setErrorMsg("");

    // Optimistic UI for user message
    const tempUserMsg: Message = {
      message_id: `temp_${Date.now()}`,
      role: "USER",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await apiFetch<any>(`/api/v1/copilot/sessions/${activeSessionId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: textToSend }),
      });

      const asstMsg: Message = {
        message_id: res.message_id,
        role: "ASSISTANT",
        content: res.content,
        citations: res.citations || [],
        actions: res.actions || [],
        created_at: res.created_at,
      };
      setMessages((prev) => [...prev, asstMsg]);
      loadReadiness();
    } catch (err: any) {
      setErrorMsg(err.message || "Copilot query failed. Please check your prompt credits.");
    } finally {
      setLoading(false);
    }
  }

  function handleActionClick(action: Action) {
    if (action.action === "NAVIGATE_DISCOVER") {
      onNavigate("discover");
    } else if (action.action === "NAVIGATE_ACCOUNT") {
      onNavigate("account");
    } else if (action.action === "NAVIGATE_APPLICATIONS") {
      onNavigate("applications");
    } else if (action.action === "SEND_PROMPT" && action.data?.prompt) {
      handleSendMessage(action.data.prompt);
    } else if (action.action === "CREATE_APPLICATION" && action.data?.opportunity_id) {
      apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({ opportunity_id: action.data.opportunity_id }),
      }).then(() => onNavigate("applications"));
    }
  }

  const promptSuggestions = [
    "Assess my funding readiness & highlight gaps",
    "Find top verified grants for my sector",
    "What documents do underwriters need for loans?",
    "Draft proposal outline for top matched grant",
  ];

  return (
    <div style={{ display: "flex", height: "calc(100vh - 70px)", backgroundColor: "var(--bg-primary)" }}>
      {/* Sessions Sidebar */}
      <aside
        style={{
          width: 280,
          borderRight: "1px solid var(--border-subtle)",
          backgroundColor: "var(--bg-secondary)",
          display: "flex",
          flexDirection: "column",
          padding: "16px 12px",
          gap: 12,
        }}
      >
        <button
          type="button"
          className="btn btn-sm"
          style={{ width: "100%", justifyContent: "center", gap: 8 }}
          onClick={createNewSession}
        >
          <PlusCircle size={15} /> New Consultation
        </button>

        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", padding: "6px 8px" }}>
          Conversation Threads
        </div>

        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
          {sessions.map((s) => (
            <button
              key={s.session_id}
              type="button"
              className={`sidebar-link ${activeSessionId === s.session_id ? "active" : ""}`}
              style={{
                textAlign: "left",
                justifyContent: "flex-start",
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: activeSessionId === s.session_id ? "#C69D49" : "transparent",
                color: activeSessionId === s.session_id ? "#000000" : "var(--text-secondary)",
                fontWeight: activeSessionId === s.session_id ? 700 : 500,
                fontSize: 13,
                border: "none",
                cursor: "pointer",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              onClick={() => selectSession(s.session_id)}
            >
              {s.title}
            </button>
          ))}
        </div>

        {/* Readiness Meter in Sidebar */}
        {readiness && (
          <div
            style={{
              padding: "14px 16px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-card)",
              border: "1px solid rgba(198, 157, 73, 0.3)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <div className="row-between">
              <span className="row" style={{ gap: 6, fontSize: 11, fontWeight: 700, color: "var(--accent-gold-bright)" }}>
                <ShieldCheck size={14} /> Readiness Score
              </span>
              <span className="mono gold-text" style={{ fontSize: 14, fontWeight: 800 }}>
                {readiness.readiness_score}/100
              </span>
            </div>
            <div style={{ width: "100%", height: 5, backgroundColor: "#222", borderRadius: 3, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${readiness.readiness_score}%`,
                  backgroundColor: "#C69D49",
                }}
              />
            </div>
            <span className="muted" style={{ fontSize: 10, textTransform: "capitalize" }}>
              {readiness.readiness_level.replace(/_/g, " ").toLowerCase()}
            </span>
          </div>
        )}
      </aside>

      {/* Main Chat Workspace */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%" }}>
        {/* Header */}
        <header
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "var(--bg-card)",
          }}
        >
          <div className="row" style={{ gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: "50%",
                backgroundColor: "rgba(198, 157, 73, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid #C69D49",
              }}
            >
              <Sparkles size={17} color="#C69D49" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#FFFFFF" }}>AURELIA</div>
              <div className="muted" style={{ fontSize: 11 }}>
                Funding Intelligence · Your intelligent funding partner
              </div>
            </div>
          </div>

          <div className="row" style={{ gap: 8 }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate("account")}
            >
              Business Profile
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate("billing")}
            >
              Plan Entitlements
            </button>
          </div>
        </header>

        {/* 8-Stage Funding Journey Ribbon */}
        <div
          style={{
            padding: "8px 24px",
            backgroundColor: "rgba(198, 157, 73, 0.08)",
            borderBottom: "1px solid rgba(198, 157, 73, 0.2)",
            display: "flex",
            alignItems: "center",
            gap: 6,
            overflowX: "auto",
            whiteSpace: "nowrap",
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          {[
            { id: "DISCOVER", label: "1. Discover" },
            { id: "MATCH", label: "2. Match" },
            { id: "UNDERSTAND", label: "3. Understand" },
            { id: "PREPARE", label: "4. Prepare" },
            { id: "REVIEW", label: "5. Review" },
            { id: "APPROVE", label: "6. Approve" },
            { id: "SUBMIT", label: "7. Submit" },
            { id: "TRACK", label: "8. Track" },
          ].map((st, i) => (
            <span
              key={st.id}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                padding: "3px 8px",
                borderRadius: 4,
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                color: "var(--accent-gold-bright)",
                border: "1px solid rgba(198, 157, 73, 0.25)",
              }}
            >
              {st.label}
              {i < 7 && <span style={{ color: "var(--text-muted)", marginLeft: 4 }}>→</span>}
            </span>
          ))}
        </div>

        {/* Message Thread */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", margin: "auto", maxWidth: 560, display: "flex", flexDirection: "column", gap: 16 }}>
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: "50%",
                  backgroundColor: "rgba(198, 157, 73, 0.12)",
                  border: "1.5px solid #C69D49",
                  margin: "0 auto",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Sparkles size={26} color="#C69D49" />
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: "#FFFFFF" }}>
                Welcome to AURELIA Funding Intelligence
              </h2>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                I am AURELIA, your intelligent funding partner on CARAVAN. I guide you across our 8-stage funding journey (Discover → Match → Understand → Prepare → Review → Approve → Submit → Track), analyze your business profile, evaluate eligibility gaps, and draft validated applications with zero hallucination.
              </p>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 8 }}>
                {promptSuggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    className="pill"
                    style={{
                      cursor: "pointer",
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-card)",
                      color: "var(--text-secondary)",
                      fontSize: 12,
                      padding: "8px 14px",
                    }}
                    onClick={() => handleSendMessage(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div
              key={m.message_id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: m.role === "USER" ? "flex-end" : "flex-start",
                gap: 8,
              }}
            >
              <div
                style={{
                  maxWidth: "82%",
                  padding: "16px 20px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: m.role === "USER" ? "rgba(198, 157, 73, 0.15)" : "var(--bg-card)",
                  border: m.role === "USER" ? "1px solid rgba(198, 157, 73, 0.4)" : "1px solid var(--border-subtle)",
                  color: "#FFFFFF",
                  fontSize: 14,
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                <div className="row" style={{ gap: 6, marginBottom: 8, fontSize: 11, color: "var(--text-muted)" }}>
                  {m.role === "USER" ? <User size={13} /> : <Bot size={13} color="var(--accent-gold-bright)" />}
                  <span>{m.role === "USER" ? "You" : "AURELIA"}</span>
                </div>
                {m.content}

                {/* Citations Cards */}
                {m.citations && m.citations.length > 0 && (
                  <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-gold-bright)", textTransform: "uppercase" }}>
                      Verified Catalogue Citations
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {m.citations.map((c) => (
                        <div
                          key={c.opportunity_id}
                          style={{
                            padding: "10px 14px",
                            backgroundColor: "var(--bg-secondary)",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border-subtle)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                          }}
                        >
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 700, color: "#FFFFFF" }}>{c.title}</div>
                            <div className="muted" style={{ fontSize: 11 }}>
                              {c.provider} · <span className="gold-text mono">{c.amount_display}</span>
                            </div>
                          </div>
                          <a
                            href={c.official_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "4px 8px", fontSize: 11 }}
                          >
                            Source <ExternalLink size={11} />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Actions */}
                {m.actions && m.actions.length > 0 && (
                  <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {m.actions.map((act, i) => (
                      <button
                        key={i}
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: 12, padding: "6px 12px" }}
                        onClick={() => handleActionClick(act)}
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="row" style={{ gap: 8, color: "var(--accent-gold-bright)", fontSize: 13, paddingLeft: 8 }}>
              <Sparkles size={16} className="spin" />
              <span>AURELIA is analysing your funding options...</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        {errorMsg && (
          <div style={{ padding: "8px 24px", backgroundColor: "rgba(239, 68, 68, 0.15)", color: "#F87171", fontSize: 12 }}>
            {errorMsg}
          </div>
        )}

        <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)" }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: "flex", gap: 10 }}
          >
            <input
              type="text"
              className="input"
              placeholder="Ask AURELIA: 'What grants match my business stage?', 'Assess my eligibility', 'Draft proposal outline'..."
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button
              type="submit"
              className="btn"
              disabled={loading || !inputPrompt.trim()}
              style={{ padding: "0 20px" }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};
