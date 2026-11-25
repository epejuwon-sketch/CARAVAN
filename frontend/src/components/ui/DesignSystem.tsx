import React from "react";
import { CheckCircle2, Clock, AlertTriangle, X, HelpCircle } from "lucide-react";

export function StatusBadge({ status }: { status: string }) {
  const s = (status || "").toUpperCase();
  let pillClass = "pill";
  let icon = null;

  switch (s) {
    case "VERIFIED":
    case "APPROVED":
    case "ACTIVE":
    case "AWARDED":
    case "STRONG":
      pillClass = "pill pill-emerald";
      icon = <CheckCircle2 size={11} />;
      break;

    case "PENDING":
    case "DRAFTING":
    case "DOCS_COLLECTING":
    case "MODERATE":
    case "IN_PREPARATION":
      pillClass = "pill pill-gold";
      icon = <Clock size={11} />;
      break;

    case "UNDER REVIEW":
    case "UNDER_REVIEW":
    case "SUBMITTED":
    case "REVIEW":
      pillClass = "pill pill-cyan";
      icon = <Clock size={11} />;
      break;

    case "EXPIRED":
    case "CLOSED":
    case "REJECTED":
    case "INELIGIBLE":
    case "PAST_DUE":
      pillClass = "pill pill-rose";
      icon = <AlertTriangle size={11} />;
      break;

    default:
      pillClass = "pill";
  }

  // Format readable label: e.g. "UNDER_REVIEW" -> "Under Review"
  const formatted = s
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");

  return (
    <span className={pillClass}>
      {icon}
      <span>{formatted}</span>
    </span>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  tone?: "default" | "gold" | "success" | "info" | "warning";
  delta?: { value: string; isPositive: boolean };
}

export function MetricCard({
  label,
  value,
  sub,
  icon,
  tone = "default",
  delta,
}: MetricCardProps) {
  let valColor = "var(--text-primary)";
  if (tone === "gold") valColor = "var(--accent-gold-bright)";
  if (tone === "success") valColor = "var(--status-success-text)";
  if (tone === "info") valColor = "var(--status-info-text)";
  if (tone === "warning") valColor = "var(--status-warning-text)";

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        position: "relative",
      }}
    >
      <div className="row-between" style={{ alignItems: "flex-start" }}>
        <span className="muted" style={{ fontSize: 12, fontWeight: 600 }}>
          {label}
        </span>
        {icon && (
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-gold-bright)",
            }}
          >
            {icon}
          </div>
        )}
      </div>

      <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
        <span style={{ fontSize: 26, fontWeight: 800, color: valColor, letterSpacing: "-0.02em" }}>
          {value}
        </span>
        {delta && (
          <span
            className="mono"
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: delta.isPositive ? "var(--status-success-text)" : "var(--status-error-text)",
            }}
          >
            {delta.isPositive ? "+" : ""}{delta.value}
          </span>
        )}
      </div>

      {sub && (
        <span className="muted" style={{ fontSize: 12, marginTop: -2 }}>
          {sub}
        </span>
      )}
    </div>
  );
}

interface DrawerProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Drawer({ open, title, onClose, children }: DrawerProps) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.8)",
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
          maxWidth: 640,
          height: "100%",
          backgroundColor: "var(--bg-secondary)",
          borderLeft: "1px solid var(--border-subtle)",
          padding: "24px 28px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 20,
          boxShadow: "var(--shadow-lg)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="row-between" style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>{title}</h2>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            style={{ padding: "6px 10px" }}
          >
            <X size={16} />
          </button>
        </div>
        <div style={{ flex: 1 }}>{children}</div>
      </div>
    </div>
  );
}

interface StepperProps {
  steps: string[];
  currentStep: number; // 1-indexed
  onStepClick?: (step: number) => void;
}

export function Stepper({ steps, currentStep, onStepClick }: StepperProps) {
  return (
    <div className="stepper">
      {steps.map((label, idx) => {
        const stepNum = idx + 1;
        const isActive = stepNum === currentStep;
        const isCompleted = stepNum < currentStep;

        return (
          <div
            key={label}
            className="step-item"
            style={{ cursor: onStepClick ? "pointer" : "default" }}
            onClick={() => onStepClick && onStepClick(stepNum)}
          >
            <div className={`step-circle ${isActive ? "active" : isCompleted ? "completed" : ""}`}>
              {isCompleted ? <CheckCircle2 size={16} /> : stepNum}
            </div>
            <span className={`step-label ${isActive ? "active" : ""}`}>{label}</span>
          </div>
        );
      })}
    </div>
  );
}

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon = <HelpCircle size={32} />,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div
      className="card"
      style={{
        textAlign: "center",
        padding: "48px 24px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
        backgroundColor: "var(--bg-secondary)",
      }}
    >
      <div style={{ color: "var(--accent-gold-bright)", opacity: 0.85, marginBottom: 4 }}>
        {icon}
      </div>
      <h3 style={{ fontSize: 16, fontWeight: 700 }}>{title}</h3>
      <p className="muted" style={{ fontSize: 13, maxWidth: 440, lineHeight: 1.6 }}>
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          type="button"
          className="btn btn-sm"
          onClick={onAction}
          style={{ marginTop: 8 }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
