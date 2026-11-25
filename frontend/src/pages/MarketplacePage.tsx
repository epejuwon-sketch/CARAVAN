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
  ChevronDown,
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
      if (openOnly) params.set("open_only", "true");

      const res = await apiFetch<any>(`/api/v1/opportunities?${params.toString()}`);
      setOpportunities(res.opportunities || []);
      setCategories(res.categories || []);
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
  }, [selectedCategory, geoFilter, openOnly]);

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
        body: JSON.stringify({ opportunity_id: oppId, notes: "Initiated from Marketplace" }),
      });
      onNavigate("applications");
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header (Matching Screen 3 in Reference) */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            Funding Opportunities
          </h1>
          <p className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            Find the right funding for your needs. Cryptographically verified institutional facilities.
          </p>
        </div>
        <span className="pill pill-gold">{opportunities.length} Verified Programs</span>
      </div>

      {msg && (
        <div className="pill pill-cyan" style={{ padding: "8px 14px" }}>
          {msg}
        </div>
      )}

      {/* Search Bar & Filter Toggle Button */}
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
            placeholder="Search opportunities..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadOpportunities()}
          />
        </div>

        <button
          type="button"
          className={`btn ${showFilters ? "btn" : "btn-secondary"}`}
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter size={14} /> Filter
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={loadOpportunities}
        >
          Search
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
            <label className="form-label">Funding Category</label>
            <select
              className="input"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="">All Categories (15)</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label className="form-label">Geographic Restrictions</label>
            <select
              className="input"
              value={geoFilter}
              onChange={(e) => setGeoFilter(e.target.value)}
            >
              <option value="">All Regions</option>
              <option value="Nigeria">Nigeria</option>
              <option value="Africa">Sub-Saharan Africa</option>
              <option value="Global">Global</option>
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
              <span>Open Deadlines Only</span>
            </label>
          </div>
        </div>
      )}

      {/* Opportunities List (Matching Screen 3 Cards in Reference) */}
      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 48 }}>
          Loading verified institutional funding opportunities...
        </div>
      ) : opportunities.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 48, backgroundColor: "var(--bg-secondary)" }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No matching opportunities found</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            Try clearing filters or search queries to view all verified programs.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {opportunities.map((opp) => {
            const isSaved = savedIds.has(opp.opportunity_id);
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
                }}
              >
                {/* Left: Icon & Opportunity Info */}
                <div style={{ display: "flex", alignItems: "center", gap: 16, flex: "1 1 360px" }}>
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
                      <StatusBadge status={opp.verification_status} />
                    </div>

                    <div className="muted" style={{ fontSize: 12 }}>
                      {opp.provider} · {opp.geographic_eligibility} · {opp.industry_sector}
                    </div>

                    <div className="gold-text mono" style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>
                      {opp.amount_display}
                    </div>
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
                    Details
                  </button>

                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => handleCreateApplication(opp.opportunity_id)}
                  >
                    Apply Now <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Drawer (Matching Screen 3 Details Modal) */}
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
              <StatusBadge status={selectedOpp.verification_status} />
            </div>

            <div className="card" style={{ backgroundColor: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Provider</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedOpp.provider}</span>
              </div>
              <div className="row-between">
                <span className="muted" style={{ fontSize: 12 }}>Funding Type</span>
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
                <span className="muted" style={{ fontSize: 12 }}>Deadline</span>
                <span className="mono" style={{ fontSize: 12 }}>
                  {selectedOpp.deadline_at ? new Date(selectedOpp.deadline_at).toLocaleDateString() : "Rolling Admission"}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700 }}>Applicant Eligibility</h4>
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
                <span className="muted">Cryptographic Provenance Hash:</span>
                <div className="mono" style={{ color: "var(--accent-gold-bright)", wordBreak: "break-all", marginTop: 4 }}>
                  {selectedOpp.provenance_hash}
                </div>
              </div>
            )}

            <div className="row" style={{ gap: 10, marginTop: 12 }}>
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
              <a
                href={selectedOpp.official_source_url}
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary"
              >
                <ExternalLink size={13} /> Official Portal
              </a>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
