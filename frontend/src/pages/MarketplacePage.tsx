import React, { useEffect, useState } from "react";
import {
  Search,
  Filter,
  ExternalLink,
  Bookmark,
  Sparkles,
  Calendar,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Briefcase,
  Building2,
  AlertCircle,
  FileText,
  MapPin,
  Tag,
} from "lucide-react";
import { FundingOpportunity } from "../types";
import { apiFetch } from "../lib/api";
import { StatusBadge, Drawer } from "../components/ui/DesignSystem";

interface MarketplacePageProps {
  onNavigate: (route: string) => void;
}

export const MarketplacePage: React.FC<MarketplacePageProps> = ({ onNavigate }) => {
  const [opportunities, setOpportunities] = useState<FundingOpportunity[]>([]);
  const [categories, setCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [geoFilter, setGeoFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [openOnly, setOpenOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedOpp, setSelectedOpp] = useState<FundingOpportunity | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState("");

  async function loadOpportunities() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set("query", query);
      if (selectedCategory) params.set("category", selectedCategory);
      if (geoFilter) params.set("geo", geoFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (openOnly) params.set("open_only", "true");

      const res = await apiFetch<any>(`/api/v1/opportunities?${params.toString()}`);
      if (res && Array.isArray(res.opportunities)) {
        setOpportunities(res.opportunities);
        if (res.categories) setCategories(res.categories);
      } else {
        setOpportunities([]);
      }
    } catch (err: any) {
      setMsg(err.message || "Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  }

  async function loadSaved() {
    try {
      const res = await apiFetch<any>("/api/v1/saved");
      const ids = new Set<string>((res.saved || []).map((s: any) => s.opportunity_id));
      setSavedIds(ids);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadOpportunities();
    loadSaved();
  }, [selectedCategory, geoFilter, statusFilter, openOnly]);

  async function handleToggleSave(oppId: string) {
    try {
      if (savedIds.has(oppId)) {
        setSavedIds((prev) => {
          const next = new Set(prev);
          next.delete(oppId);
          return next;
        });
      } else {
        await apiFetch("/api/v1/saved", {
          method: "POST",
          body: JSON.stringify({ opportunity_id: oppId }),
        });
        setSavedIds((prev) => new Set(prev).add(oppId));
      }
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  async function handleCreateApplication(oppId: string) {
    try {
      await apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({ opportunity_id: oppId, notes: "Initiated from Verified Marketplace" }),
      });
      onNavigate("applications");
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  function renderStatusPill(status: string) {
    const s = (status || "").toUpperCase();
    if (s === "CLOSED") {
      return <span className="pill pill-rose">CLOSED</span>;
    }
    if (s === "CLOSING_SOON") {
      return <span className="pill pill-gold">CLOSING SOON</span>;
    }
    if (s === "UPCOMING" || s === "UPCOMING_CONFIRMED") {
      return <span className="pill pill-cyan">UPCOMING</span>;
    }
    if (s === "ROLLING") {
      return <span className="pill pill-emerald">ROLLING ADMISSION</span>;
    }
    return <span className="pill pill-emerald">OPEN</span>;
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            Funding Opportunities Marketplace
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Institutional facilities across Nigeria, Africa, and International jurisdictions. Cryptographically verified against official registries.
          </p>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate("eligibility")}
          >
            <Sparkles size={13} color="var(--accent-gold-bright)" /> Check My Eligibility
          </button>
          <span className="pill pill-gold">{opportunities.length} Verified Facilities</span>
        </div>
      </div>

      {msg && (
        <div className="pill pill-cyan" style={{ padding: "8px 14px" }}>
          {msg}
        </div>
      )}

      {/* Search Bar & Filter Controls */}
      <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 300px" }}>
          <Search
            size={16}
            style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--text-muted)",
            }}
          />
          <input
            className="input"
            style={{ paddingLeft: 40 }}
            placeholder="Search by programme name, provider, keyword, sector, or criteria..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadOpportunities()}
          />
        </div>

        <button
          type="button"
          className={`btn ${showFilters ? "" : "btn-secondary"}`}
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter size={14} /> Filters
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={loadOpportunities}
        >
          Search
        </button>
      </div>

      {/* Geographic Quick Filters */}
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          className={`btn btn-sm ${geoFilter === "" ? "" : "btn-secondary"}`}
          onClick={() => setGeoFilter("")}
        >
          All Geographies
        </button>
        <button
          type="button"
          className={`btn btn-sm ${geoFilter === "Nigeria" ? "" : "btn-secondary"}`}
          onClick={() => setGeoFilter("Nigeria")}
        >
          🇳🇬 Nigeria Priority
        </button>
        <button
          type="button"
          className={`btn btn-sm ${geoFilter === "Africa" ? "" : "btn-secondary"}`}
          onClick={() => setGeoFilter("Africa")}
        >
          🌍 Pan-African
        </button>
        <button
          type="button"
          className={`btn btn-sm ${geoFilter === "Global" ? "" : "btn-secondary"}`}
          onClick={() => setGeoFilter("Global")}
        >
          🌐 Global
        </button>
      </div>

      {/* Expandable Filter Controls */}
      {showFilters && (
        <div
          className="card"
          style={{
            backgroundColor: "var(--bg-secondary)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 16,
            padding: 20,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Funding Instrument</label>
            <select
              className="input"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="">All Instruments (Grants, Loans, Equity, Prizes)</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Operating Status</label>
            <select
              className="input"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open Only</option>
              <option value="ROLLING">Rolling Admission</option>
              <option value="CLOSING_SOON">Closing Soon</option>
              <option value="UPCOMING">Upcoming</option>
              <option value="CLOSED">Closed (Historical Archive)</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6, justifyContent: "flex-end" }}>
            <label
              className="row"
              style={{ gap: 8, fontSize: 13, cursor: "pointer", paddingBottom: 10 }}
            >
              <input
                type="checkbox"
                checked={openOnly}
                onChange={(e) => setOpenOnly(e.target.checked)}
                style={{ accentColor: "var(--accent-gold)" }}
              />
              <span>Hide Closed Deadlines</span>
            </label>
          </div>
        </div>
      )}

      {/* Opportunities List */}
      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 48 }}>
          Loading verified institutional funding opportunities from primary registries...
        </div>
      ) : opportunities.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 48, backgroundColor: "var(--bg-secondary)" }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No matching opportunities found</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            Try clearing filters or search queries to view all verified programs.
          </p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ marginTop: 16 }}
            onClick={() => {
              setQuery("");
              setSelectedCategory("");
              setGeoFilter("");
              setStatusFilter("");
              setOpenOnly(false);
            }}
          >
            Clear All Filters
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {opportunities.map((opp) => {
            const isSaved = savedIds.has(opp.opportunity_id);
            const liveStatus = opp.opportunity_status || opp.verification_status;
            const isClosed = liveStatus === "CLOSED";

            return (
              <div
                key={opp.opportunity_id}
                className="card"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 16,
                  padding: "20px 24px",
                  backgroundColor: "var(--bg-card)",
                  opacity: isClosed ? 0.8 : 1.0,
                }}
              >
                {/* Left: Icon & Opportunity Info */}
                <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flex: "1 1 360px" }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: "var(--radius-sm)",
                      backgroundColor: "var(--bg-secondary)",
                      border: "1px solid var(--border-gold)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--accent-gold-bright)",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <Briefcase size={22} />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                      <strong
                        style={{ fontSize: 16, fontWeight: 700, cursor: "pointer", color: "#FFFFFF" }}
                        onClick={() => setSelectedOpp(opp)}
                      >
                        {opp.title}
                      </strong>
                      {renderStatusPill(liveStatus)}
                    </div>

                    <div className="muted" style={{ fontSize: 12 }}>
                      {opp.provider} · {opp.geographic_eligibility} · {opp.industry_sector}
                    </div>

                    <div className="gold-text mono" style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>
                      {opp.amount_display}
                    </div>

                    {opp.important_conditions && (
                      <div className="row" style={{ gap: 6, fontSize: 11, color: "#FBBF24", marginTop: 2 }}>
                        <AlertCircle size={12} />
                        <span>{opp.important_conditions.length > 90 ? `${opp.important_conditions.slice(0, 90)}...` : opp.important_conditions}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleToggleSave(opp.opportunity_id)}
                    title={isSaved ? "Saved" : "Save Opportunity"}
                  >
                    <Bookmark size={13} fill={isSaved ? "var(--accent-gold)" : "none"} color={isSaved ? "var(--accent-gold)" : "inherit"} />
                  </button>

                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setSelectedOpp(opp)}
                  >
                    Details &amp; Evidence
                  </button>

                  <button
                    type="button"
                    className={`btn btn-sm ${isClosed ? "btn-secondary" : ""}`}
                    onClick={() => handleCreateApplication(opp.opportunity_id)}
                  >
                    {isClosed ? "Track in Workspace" : "Apply Now"} <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Drawer */}
      <Drawer
        open={Boolean(selectedOpp)}
        title={selectedOpp?.title || "Opportunity Details"}
        onClose={() => setSelectedOpp(null)}
      >
        {selectedOpp && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="row-between" style={{ alignItems: "center" }}>
              <span className="gold-text mono" style={{ fontSize: 20, fontWeight: 800 }}>
                {selectedOpp.amount_display}
              </span>
              {renderStatusPill(selectedOpp.opportunity_status || selectedOpp.verification_status)}
            </div>

            {/* Fee & Important Conditions Disclosure */}
            {selectedOpp.important_conditions && (
              <div
                style={{
                  backgroundColor: "rgba(234, 179, 8, 0.08)",
                  border: "1px solid rgba(234, 179, 8, 0.3)",
                  borderRadius: "var(--radius-sm)",
                  padding: "12px 14px",
                }}
              >
                <strong style={{ color: "#FBBF24", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
                  <AlertCircle size={14} /> Third-Party Policy &amp; Fee Disclosure:
                </strong>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.5 }}>
                  {selectedOpp.important_conditions}
                </p>
              </div>
            )}

            <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Provider</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.provider}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Funding Instrument</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.funding_type}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Geographic Region</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.geographic_eligibility}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Sector Focus</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.industry_sector}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Application Method</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.application_method || "Online Portal"}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Deadline Schedule</span>
                <span className="mono" style={{ fontSize: 12 }}>
                  {selectedOpp.deadline_at ? new Date(selectedOpp.deadline_at).toLocaleDateString() : "Rolling / Continuous Intake"}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700 }}>Applicant Eligibility Criteria</h4>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
                {selectedOpp.applicant_eligibility}
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700 }}>Statutory Application Requirements</h4>
              <ul style={{ paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 6 }}>
                {(selectedOpp.application_requirements || []).map((req, i) => (
                  <li key={i}>{req}</li>
                ))}
              </ul>
            </div>

            {selectedOpp.provenance_hash && (
              <div className="card" style={{ backgroundColor: "var(--bg-primary)", fontSize: 11 }}>
                <span className="muted">Cryptographic Provenance Hash (SHA-256):</span>
                <div className="mono" style={{ color: "var(--accent-gold-bright)", wordBreak: "break-all", marginTop: 4 }}>
                  {selectedOpp.provenance_hash}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Primary Source: {selectedOpp.source_name}
                </div>
              </div>
            )}

            <div className="row" style={{ gap: 10, marginTop: 12, flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn"
                style={{ flex: 1 }}
                onClick={() => {
                  handleCreateApplication(selectedOpp.opportunity_id);
                  setSelectedOpp(null);
                }}
              >
                Apply for Funding
              </button>
              {selectedOpp.official_application_url && (
                <a
                  href={selectedOpp.official_application_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                >
                  <ExternalLink size={13} /> Official Application
                </a>
              )}
              {selectedOpp.official_source_url && selectedOpp.official_source_url !== selectedOpp.official_application_url && (
                <a
                  href={selectedOpp.official_source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                >
                  <ExternalLink size={13} /> Primary Registry
                </a>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
