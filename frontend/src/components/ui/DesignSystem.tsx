import React from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export function StatusBadge({ status }: { status: string }) {
  let pillClass = "pill";
  switch (status.toUpperCase()) {
    case "VERIFIED":
    case "ACTIVE":
    case "AWARDED":
    case "STRONG":
      pillClass = "pill pill-emerald";
      break;
    case "UNVERIFIED":
    case "DRAFTING":
    case "DOCS_COLLECTING":
    case "MODERATE":
      pillClass = "pill pill-amber";
      break;
    case "EXPIRED":
    case "CLOSED":
    case "REJECTED":
    case "PAST_DUE":
    case "INELIGIBLE":
      pillClass = "pill pill-rose";
      break;
    default:
      pillClass = "pill pill-cyan";
  }
  return <span className={pillClass}>{status}</span>;
}

export function MetricCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string | number;
  sub?: string;
  tone?: "default" | "success" | "cyan" | "amber";
}) {
  let valColor = "var(--text-primary)";
  if (tone === "success") valColor = "var(--accent-emerald)";
  if (tone === "cyan") valColor = "var(--accent-cyan)";
  if (tone === "amber") valColor = "var(--accent-amber)";

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="muted" style={{ fontSize: 12, fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, color: valColor, letterSpacing: "-0.02em" }}>
        {value}
      </div>
      {sub && <div className="muted" style={{ fontSize: 11 }}>{sub}</div>}
    </div>
  );
}

export function Drawer({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 100,
        display: "flex",
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 620,
          height: "100%",
          backgroundColor: "var(--bg-secondary)",
          borderLeft: "1px solid var(--border-subtle)",
          padding: 24,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="row-between">
          <strong style={{ fontSize: 16 }}>{title}</strong>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            <X size={14} />
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
