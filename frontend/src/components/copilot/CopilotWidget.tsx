import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  MessageSquare,
  X,
  Minus,
  Send,
  Mic,
  MicOff,
  Volume2,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  FileText,
  ShieldCheck,
  ChevronDown,
  Plus,
  ArrowRight,
} from "lucide-react";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../../lib/auth";

interface CopilotWidgetProps {
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

export const CopilotWidget: React.FC<CopilotWidgetProps> = ({ onNavigate }) => {
  const { user, token } = useAuth();
  const isAuthenticated = Boolean(user && token);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isMinimized, setIsMinimized] = useState<boolean>(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [modelLabel, setModelLabel] = useState<string>("Gemini 2.5 Active");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize sessions when widget opens and user is authenticated
  useEffect(() => {
    if (isAuthenticated && isOpen && !activeSessionId) {
      loadSessions();
    }
  }, [isAuthenticated, isOpen, activeSessionId]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, isMinimized, loading]);

  // Setup Web Speech API for voice interactions
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-NG";

        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          if (transcript) {
            setInputPrompt(transcript);
            handleSendMessage(transcript);
          }
          setIsListening(false);
        };

        recognition.onerror = () => {
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      }
    }
  }, [activeSessionId]);

  async function loadSessions() {
    if (!isAuthenticated) return;
    try {
      const data = await apiFetch<any>("/api/v1/copilot/sessions");
      const list: Session[] = data.sessions || [];
      setSessions(list);
      if (list.length > 0) {
        selectSession(list[0].session_id);
      } else {
        createNewSession();
      }
    } catch (err: any) {
      if (err.message && (err.message.includes("401") || err.message.includes("Missing authentication") || err.message.includes("credentials"))) {
        setErrorMsg("Session expired. Please sign in to resume chatting with AURELIA.");
      } else {
        setErrorMsg(err.message || "Failed to load sessions");
      }
    }
  }

  async function createNewSession() {
    if (!isAuthenticated) return;
    try {
      setLoading(true);
      setErrorMsg("");
      const newSess = await apiFetch<any>("/api/v1/copilot/sessions", {
        method: "POST",
        body: JSON.stringify({
          title: "Funding Consultation",
          context_mode: "GENERAL",
        }),
      });

      const sessObj: Session = {
        session_id: newSess.session_id,
        title: newSess.title,
        context_mode: newSess.context_mode,
        message_count: 0,
        updated_at: newSess.created_at,
      };

      setSessions((prev) => [sessObj, ...prev]);
      setActiveSessionId(newSess.session_id);

      // Initial welcome message
      setMessages([
        {
          message_id: "init_welcome",
          role: "ASSISTANT",
          content:
            "**Welcome to AURELIA Funding Intelligence.**\n\nI am your intelligent funding partner on CARAVAN. I guide you through the complete funding lifecycle:\n**DISCOVER → MATCH → UNDERSTAND → PREPARE → REVIEW → APPROVE → SUBMIT → TRACK**\n\nI can:\n- Search verified institutional funding opportunities\n- Evaluate confirmed vs. unknown eligibility criteria\n- Clarify missing profile details and audit required documents\n- Draft validated application answers with cryptographic approval gating",
          citations: [],
          actions: [
            { label: "8-Stage Journey", action: "SEND_PROMPT", data: { prompt: "Explain the 8-stage funding journey and where my business stands" } },
            { label: "Discover Grants", action: "SEND_PROMPT", data: { prompt: "What verified grants are available for my business?" } },
            { label: "Readiness Diagnostic", action: "SEND_PROMPT", data: { prompt: "Run full business readiness diagnostic" } },
            { label: "Document Audit", action: "SEND_PROMPT", data: { prompt: "Audit my document checklist" } },
          ],
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      if (err.message && (err.message.includes("401") || err.message.includes("Missing authentication") || err.message.includes("credentials"))) {
        setErrorMsg("Session expired. Please sign in to resume chatting with AURELIA.");
      } else {
        setErrorMsg(err.message || "Could not start new conversation with AURELIA");
      }
    } finally {
      setLoading(false);
    }
  }

  async function selectSession(sessionId: string) {
    if (!isAuthenticated) return;
    setActiveSessionId(sessionId);
    setErrorMsg("");
    try {
      setLoading(true);
      const data = await apiFetch<any>(`/api/v1/copilot/sessions/${sessionId}/messages`);
      const msgs = data.messages || [];
      if (msgs.length === 0) {
        setMessages([
          {
            message_id: "init_empty",
            role: "ASSISTANT",
            content: "How can AURELIA assist your funding journey today?",
            actions: [
              { label: "Find Opportunities", action: "SEND_PROMPT", data: { prompt: "Show verified opportunities for my sector" } },
              { label: "Check Readiness Score", action: "SEND_PROMPT", data: { prompt: "What is my business readiness score?" } },
            ],
            created_at: new Date().toISOString(),
          },
        ]);
      } else {
        setMessages(msgs);
      }
    } catch (err: any) {
      if (err.message && (err.message.includes("401") || err.message.includes("Missing authentication") || err.message.includes("credentials"))) {
        setErrorMsg("Session expired. Please sign in to resume chatting with AURELIA.");
      } else {
        setErrorMsg(err.message || "Failed to retrieve conversation history");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage(overrideText?: string) {
    if (!isAuthenticated) return;
    const textToSend = (overrideText || inputPrompt).trim();
    if (!textToSend || loading) return;

    if (!activeSessionId) {
      await createNewSession();
    }

    const optimisticMsg: Message = {
      message_id: `temp_${Date.now()}`,
      role: "USER",
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMsg]);
    setInputPrompt("");
    setLoading(true);
    setErrorMsg("");

    try {
      const data = await apiFetch<any>(`/api/v1/copilot/sessions/${activeSessionId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: textToSend }),
      });

      const asstMsg: Message = {
        message_id: data.message_id || `asst_${Date.now()}`,
        role: "ASSISTANT",
        content: data.content,
        citations: data.citations || [],
        actions: data.actions || [],
        created_at: data.created_at || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, asstMsg]);

      if (data.provider_used && data.provider_used.includes("gemini")) {
        setModelLabel("Gemini 2.5 Active");
      } else {
        setModelLabel("CARAVAN AI Engine");
      }

      // Voice read aloud if voice mode active
      if (isVoiceActive && typeof window !== "undefined" && "speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(data.content.replace(/[#*_`-]/g, " ").slice(0, 300));
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
      }
    } catch (err: any) {
      if (err.message && (err.message.includes("401") || err.message.includes("Missing authentication") || err.message.includes("credentials"))) {
        setErrorMsg("Session expired. Please sign in to resume chatting with AURELIA.");
      } else {
        setErrorMsg(err.message || "AURELIA is momentarily busy. Please click Retry.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleActionClick(action: Action) {
    if (action.action === "SEND_PROMPT") {
      handleSendMessage(action.data?.prompt);
    } else if (action.action === "NAVIGATE_DISCOVER") {
      onNavigate("discover");
    } else if (action.action === "NAVIGATE_APPLICATIONS") {
      onNavigate("applications");
    } else if (action.action === "NAVIGATE_ACCOUNT") {
      onNavigate("account");
    } else if (action.action === "START_APPLICATION_AGENT") {
      handleSendMessage(`Launch 13-Step Application Agent for opportunity ${action.data?.opportunity_id}`);
    } else if (action.action === "CHECK_DOCS") {
      handleSendMessage("Audit my document readiness checklist");
    }
  }

  function toggleVoiceInput() {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      if (recognitionRef.current) {
        setIsListening(true);
        recognitionRef.current.start();
      } else {
        alert("Voice recognition is not supported in this browser. Please use text input.");
      }
    }
  }

  function speakMessage(text: string) {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const clean = text.replace(/[#*_`-]/g, " ").slice(0, 400);
      const utterance = new SpeechSynthesisUtterance(clean);
      window.speechSynthesis.speak(utterance);
    }
  }

  return (
    <>
      {/* Floating Action Button in Bottom-Right Corner */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => {
            setIsOpen(true);
            setIsMinimized(false);
          }}
          className="copilot-floating-btn"
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 18px",
            borderRadius: 9999,
            backgroundColor: "#C69D49",
            color: "#050505",
            border: "1px solid rgba(255, 255, 255, 0.25)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6), 0 0 16px rgba(198, 157, 73, 0.35)",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: 13,
            transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
          title="Open AURELIA Funding Intelligence"
        >
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Sparkles size={18} />
            <span
              style={{
                position: "absolute",
                top: -3,
                right: -3,
                width: 7,
                height: 7,
                borderRadius: "50%",
                backgroundColor: isAuthenticated ? "#22C55E" : "#C69D49",
                boxShadow: isAuthenticated ? "0 0 6px #22C55E" : "0 0 6px #C69D49",
              }}
            />
          </div>
          <span>Ask AURELIA</span>
        </button>
      )}

      {/* Expanded / Floating Conversational Interface */}
      {isOpen && (
        <div
          className="copilot-chat-window"
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            zIndex: 10000,
            width: "min(440px, calc(100vw - 32px))",
            height: isMinimized ? "auto" : "min(640px, calc(100vh - 48px))",
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-gold)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "0 16px 40px rgba(0, 0, 0, 0.85), 0 0 24px rgba(198, 157, 73, 0.15)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            animation: "fadeInUp 0.2s ease-out",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "14px 16px",
              backgroundColor: "var(--bg-card)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "rgba(198, 157, 73, 0.15)",
                  border: "1px solid var(--border-gold)",
                  color: "var(--accent-gold)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Sparkles size={17} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                    AURELIA
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      padding: "2px 6px",
                      borderRadius: 4,
                      backgroundColor: isAuthenticated ? "rgba(34, 197, 94, 0.15)" : "rgba(198, 157, 73, 0.15)",
                      color: isAuthenticated ? "#4ADE80" : "var(--accent-gold-bright)",
                      border: isAuthenticated ? "1px solid rgba(34, 197, 94, 0.3)" : "1px solid rgba(198, 157, 73, 0.3)",
                    }}
                  >
                    {isAuthenticated ? modelLabel : "Sign In Required"}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  Funding Intelligence · Your intelligent funding partner
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {/* Voice mode toggle */}
              <button
                type="button"
                onClick={() => setIsVoiceActive(!isVoiceActive)}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: isVoiceActive ? "rgba(198, 157, 73, 0.2)" : "transparent",
                  color: isVoiceActive ? "var(--accent-gold)" : "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
                title={isVoiceActive ? "Voice Audio Readout Active" : "Enable Voice Readout"}
              >
                <Volume2 size={15} />
              </button>

              {/* New session */}
              <button
                type="button"
                onClick={createNewSession}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
                title="Start New Conversation"
              >
                <Plus size={16} />
              </button>

              {/* Minimize */}
              <button
                type="button"
                onClick={() => setIsMinimized(!isMinimized)}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
                title={isMinimized ? "Expand" : "Minimize"}
              >
                <Minus size={16} />
              </button>

              {/* Close */}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
                title="Close"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* 8-Stage Funding Journey Ribbon */}
          <div
            style={{
              padding: "7px 12px",
              backgroundColor: "rgba(198, 157, 73, 0.08)",
              borderBottom: "1px solid rgba(198, 157, 73, 0.2)",
              display: "flex",
              alignItems: "center",
              gap: 4,
              overflowX: "auto",
              whiteSpace: "nowrap",
              fontSize: 10,
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
                  gap: 3,
                  padding: "2px 6px",
                  borderRadius: 4,
                  backgroundColor: "rgba(255, 255, 255, 0.04)",
                  color: "var(--accent-gold-bright)",
                  border: "1px solid rgba(198, 157, 73, 0.25)",
                }}
              >
                {st.label}
                {i < 7 && <span style={{ color: "var(--text-muted)", marginLeft: 2 }}>→</span>}
              </span>
            ))}
          </div>

          {/* Body */}
          {!isMinimized && (
            !isAuthenticated ? (
              <div
                style={{
                  flex: 1,
                  padding: "32px 24px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  gap: 16,
                  backgroundColor: "var(--bg-primary)",
                }}
              >
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    backgroundColor: "rgba(198, 157, 73, 0.12)",
                    border: "1.5px solid #C69D49",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--accent-gold)",
                    boxShadow: "0 0 24px rgba(198, 157, 73, 0.2)",
                  }}
                >
                  <Sparkles size={26} />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 800, color: "#FFFFFF", margin: 0 }}>
                    Sign in to chat with AURELIA
                  </h3>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5, margin: 0, maxWidth: 320 }}>
                    AURELIA Funding Intelligence is reserved for authenticated accounts. Sign in to access multi-turn funding diagnostics, verified institutional grants, and automated application drafting.
                  </p>
                </div>

                <div
                  style={{
                    width: "100%",
                    padding: "14px 16px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid var(--border-subtle)",
                    textAlign: "left",
                    fontSize: 12,
                    color: "var(--text-secondary)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    margin: "4px 0",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent-gold-bright)" }}>
                    <CheckCircle2 size={14} />
                    <span>Search 35+ verified institutional grants & loans</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent-gold-bright)" }}>
                    <CheckCircle2 size={14} />
                    <span>Zero-hallucination eligibility matching</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent-gold-bright)" }}>
                    <CheckCircle2 size={14} />
                    <span>Vault document audits & readiness scores</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent-gold-bright)" }}>
                    <CheckCircle2 size={14} />
                    <span>13-step cryptographic application drafting</span>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", marginTop: 4 }}>
                  <button
                    type="button"
                    onClick={() => {
                      setIsOpen(false);
                      onNavigate("login");
                    }}
                    className="btn btn-lg"
                    style={{ width: "100%", justifyContent: "center" }}
                  >
                    Sign In to CARAVAN
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIsOpen(false);
                      onNavigate("register");
                    }}
                    className="btn btn-secondary"
                    style={{ width: "100%", justifyContent: "center" }}
                  >
                    Create Enterprise Account
                  </button>
                </div>
              </div>
            ) : (
              <>
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                  backgroundColor: "var(--bg-primary)",
                }}
              >
                {messages.map((m, idx) => (
                  <div
                    key={m.message_id || idx}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: m.role === "USER" ? "flex-end" : "flex-start",
                      maxWidth: "100%",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "92%",
                        padding: "12px 15px",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: m.role === "USER" ? "#1C1C1C" : "var(--bg-card)",
                        border:
                          m.role === "USER"
                            ? "1px solid var(--border-medium)"
                            : "1px solid var(--border-subtle)",
                        color: "var(--text-primary)",
                        fontSize: 13,
                        lineHeight: 1.6,
                      }}
                    >
                      {/* Message Content */}
                      <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                        {m.content}
                      </div>

                      {/* Verified Opportunity Cards in Assistant responses */}
                      {m.citations && m.citations.length > 0 && (
                        <div
                          style={{
                            marginTop: 12,
                            paddingTop: 10,
                            borderTop: "1px solid var(--border-subtle)",
                            display: "flex",
                            flexDirection: "column",
                            gap: 8,
                          }}
                        >
                          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-gold)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                            Verified Registry Citations:
                          </div>
                          {m.citations.map((c) => (
                            <div
                              key={c.opportunity_id}
                              style={{
                                padding: 10,
                                borderRadius: "var(--radius-sm)",
                                backgroundColor: "rgba(255, 255, 255, 0.03)",
                                border: "1px solid var(--border-subtle)",
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                                <div style={{ fontWeight: 700, fontSize: 12, color: "var(--text-primary)" }}>
                                  {c.title}
                                </div>
                                <span style={{ fontSize: 10, color: "var(--accent-gold)", fontWeight: 700 }}>
                                  {c.funding_type}
                                </span>
                              </div>
                              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                                {c.provider} • <span style={{ color: "#4ADE80" }}>{c.amount_display}</span>
                              </div>
                              <div style={{ marginTop: 6, display: "flex", gap: 10 }}>
                                <a
                                  href={c.official_source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    fontSize: 11,
                                    color: "var(--accent-gold-bright)",
                                    textDecoration: "none",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 3,
                                  }}
                                >
                                  Official Source <ExternalLink size={11} />
                                </a>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Action buttons */}
                      {m.actions && m.actions.length > 0 && (
                        <div
                          style={{
                            marginTop: 10,
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 6,
                          }}
                        >
                          {m.actions.map((act, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => handleActionClick(act)}
                              style={{
                                fontSize: 11,
                                fontWeight: 600,
                                padding: "4px 10px",
                                borderRadius: "var(--radius-full)",
                                backgroundColor: "rgba(198, 157, 73, 0.12)",
                                color: "var(--accent-gold-bright)",
                                border: "1px solid var(--border-gold)",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              <span>{act.label}</span>
                              <ArrowRight size={11} />
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Audio listen helper for assistant */}
                      {m.role === "ASSISTANT" && (
                        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
                          <button
                            type="button"
                            onClick={() => speakMessage(m.content)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: 4,
                              fontSize: 10,
                            }}
                            title="Read Aloud"
                          >
                            <Volume2 size={12} />
                            <span>Listen</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Loading indicator */}
                {loading && (
                  <div
                    style={{
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      alignSelf: "flex-start",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      fontSize: 12,
                      color: "var(--text-secondary)",
                    }}
                  >
                    <div className="spinner" style={{ width: 14, height: 14, border: "2px solid var(--accent-gold)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                    <span>AURELIA is analysing your funding options...</span>
                  </div>
                )}

                {/* Error Banner with Retry / Sign In */}
                {errorMsg && (
                  <div
                    style={{
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "rgba(239, 68, 68, 0.12)",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      color: "#F87171",
                      fontSize: 12,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <AlertCircle size={15} />
                      <span>{errorMsg}</span>
                    </div>
                    {errorMsg.includes("sign in") || errorMsg.includes("Session expired") ? (
                      <button
                        type="button"
                        onClick={() => {
                          setIsOpen(false);
                          onNavigate("login");
                        }}
                        style={{
                          padding: "4px 10px",
                          borderRadius: 4,
                          backgroundColor: "#C69D49",
                          color: "#050505",
                          border: "none",
                          fontWeight: 700,
                          fontSize: 11,
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Sign In
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleSendMessage()}
                        style={{
                          padding: "3px 8px",
                          borderRadius: 4,
                          backgroundColor: "#EF4444",
                          color: "white",
                          border: "none",
                          fontWeight: 600,
                          fontSize: 11,
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Retry
                      </button>
                    )}
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              {/* Quick Prompt Suggestions */}
              <div
                style={{
                  padding: "6px 12px",
                  backgroundColor: "var(--bg-card)",
                  borderTop: "1px solid var(--border-subtle)",
                  display: "flex",
                  gap: 6,
                  overflowX: "auto",
                  whiteSpace: "nowrap",
                }}
              >
                <button
                  type="button"
                  onClick={() => handleSendMessage("What grants are open for Nigerian agribusinesses?")}
                  style={{
                    fontSize: 11,
                    padding: "4px 8px",
                    borderRadius: 4,
                    backgroundColor: "transparent",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                  }}
                >
                  🌾 Agribusiness Grants
                </button>
                <button
                  type="button"
                  onClick={() => handleSendMessage("Am I eligible for BOI RAPID loan?")}
                  style={{
                    fontSize: 11,
                    padding: "4px 8px",
                    borderRadius: 4,
                    backgroundColor: "transparent",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                  }}
                >
                  ⚡ BOI RAPID Eligibility
                </button>
                <button
                  type="button"
                  onClick={() => handleSendMessage("Audit my document readiness checklist")}
                  style={{
                    fontSize: 11,
                    padding: "4px 8px",
                    borderRadius: 4,
                    backgroundColor: "transparent",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                  }}
                >
                  📁 Vault Document Audit
                </button>
              </div>

              {/* Input Area */}
              <div
                style={{
                  padding: 12,
                  backgroundColor: "var(--bg-secondary)",
                  borderTop: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {/* Voice recording button */}
                <button
                  type="button"
                  onClick={toggleVoiceInput}
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    border: isListening ? "2px solid #EF4444" : "1px solid var(--border-subtle)",
                    backgroundColor: isListening ? "rgba(239, 68, 68, 0.2)" : "var(--bg-card)",
                    color: isListening ? "#EF4444" : "var(--accent-gold)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    animation: isListening ? "pulse 1.2s infinite" : "none",
                  }}
                  title={isListening ? "Listening... click to stop" : "Speak your query (Speech-to-Text)"}
                >
                  {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                </button>

                <textarea
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder={isListening ? "Listening to your voice..." : "Ask AURELIA about opportunities, criteria, documents..."}
                  rows={1}
                  style={{
                    flex: 1,
                    resize: "none",
                    padding: "9px 12px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    fontFamily: "inherit",
                    outline: "none",
                  }}
                />

                <button
                  type="button"
                  onClick={() => handleSendMessage()}
                  disabled={!inputPrompt.trim() || loading}
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    backgroundColor: inputPrompt.trim() && !loading ? "#C69D49" : "var(--bg-card)",
                    color: inputPrompt.trim() && !loading ? "#050505" : "var(--text-muted)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: inputPrompt.trim() && !loading ? "pointer" : "default",
                    transition: "all 0.2s ease",
                  }}
                  title="Send message"
                >
                  <Send size={16} />
                </button>
              </div>
            </>
            )
          )}
        </div>
      )}
    </>
  );
};
