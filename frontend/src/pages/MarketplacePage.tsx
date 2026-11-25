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
        // Find saved record or toggle
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
      {/* Header */}
      <div className="row-between" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800 }}>Funding Intelligence Marketplace</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Verified non-dilutive grants, venture equity, concessionary debt, and institutional awards.
          </p>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate("eligibility")}>
            <Sparkles size={13} /> Run Matching Scorecard
          </button>
        </div>
      </div>

      {msg && (
        <div className="pill pill-rose" style={{ alignSelf: "flex-start" }}>
          {msg}
        </div>
      )}

      {/* Search & Filters Controls */}
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
            <input
              className="input"
              placeholder="Search by title, provider, or keyword..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadOpportunities()}
            />
          </div>
          <button type="button" className="btn btn-sm" onClick={loadOpportunities}>
            <Search size={13} /> Search
          </button>
        </div>

        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          <select
            className="input"
            style={{ width: "auto", minWidth: 180 }}
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="">All 15 Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>

          <select
            className="input"
            style={{ width: "auto", minWidth: 160 }}
            value={geoFilter}
            onChange={(e) => setGeoFilter(e.target.value)}
          >
            <option value="">All Geographies</option>
            <option value="Nigeria">Nigeria</option>
            <option value="Africa">Pan-African</option>
            <option value="United Kingdom">United Kingdom</option>
            <option value="Global">Global</option>
          </select>

          <label className="row" style={{ gap: 6, fontSize: 13, cursor: "pointer", marginLeft: "auto" }}>
            <input
              type="checkbox"
              checked={openOnly}
              onChange={(e) => setOpenOnly(e.target.checked)}
            />
            <span>Open Deadlines Only</span>
          </label>
        </div>
      </div>

      {/* Opportunities Grid */}
      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading verified institutional funding opportunities...
        </div>
      ) : opportunities.length === 0 ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          No funding opportunities matching your filter criteria.
        </div>
      ) : (
        <div className="grid-2" style={{ gap: 16 }}>
          {opportunities.map((opp) => {
            const isSaved = savedIds.has(opp.opportunity_id);
            return (
              <div
                key={opp.opportunity_id}
                className="card card-interactive"
                style={{ display: "flex", flexDirection: "column", gap: 14 }}
              >
                <div className="row-between">
                  <div className="row" style={{ gap: 6 }}>
                    <span className="pill pill-cyan">{opp.funding_type}</span>
                    <StatusBadge status={opp.verification_status} />
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    title={isSaved ? "Saved" : "Save opportunity"}
                    onClick={() => handleToggleSave(opp.opportunity_id)}
                  >
                    <Bookmark size={13} fill={isSaved ? "var(--accent-cyan)" : "none"} color={isSaved ? "var(--accent-cyan)" : "currentColor"} />
                  </button>
                </div>

                <div>
                  <strong style={{ fontSize: 16, lineHeight: 1.4 }}>{opp.title}</strong>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    Provided by {opp.provider} · {opp.geographic_eligibility}
                  </div>
                </div>

                <div className="row" style={{ gap: 12, fontSize: 12 }}>
                  <div className="mono" style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>
                    {opp.amount_display}
                  </div>
                  {opp.deadline_at && (
                    <div className="row muted" style={{ gap: 4 }}>
                      <Clock size={12} /> Deadline: {new Date(opp.deadline_at).toLocaleDateString()}
                    </div>
                  )}
                </div>

                <p className="muted" style={{ fontSize: 12, lineHeight: 1.5, flex: 1 }}>
                  {opp.applicant_eligibility.slice(0, 160)}...
                </p>

                <div className="row" style={{ gap: 8, marginTop: 4 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setSelectedOpp(opp)}
                  >
                    Inspect Opportunity
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => handleCreateApplication(opp.opportunity_id)}
                  >
                    Start Workspace <ArrowRight size={12} />
                  </button>
                  <a
                    href={opp.official_source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-secondary btn-sm"
                    style={{ marginLeft: "auto" }}
                    title="Official Registry"
                  >
                    <ExternalLink size={12} />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Opportunity Detail Drawer */}
      <Drawer
        open={Boolean(selectedOpp)}
        title={selectedOpp?.title || "Opportunity Details"}
        onClose={() => setSelectedOpp(null)}
      >
        {selectedOpp && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 13 }}>
            <div className="row" style={{ gap: 8 }}>
              <span className="pill pill-cyan">{selectedOpp.funding_type}</span>
              <StatusBadge status={selectedOpp.verification_status} />
              <span className="pill pill-emerald"><ShieldCheck size={12} /> Provenance Verified</span>
            </div>

            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div className="muted" style={{ fontSize: 11 }}>FUNDING AMOUNT &amp; CURRENCY</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "var(--accent-emerald)" }}>
                {selectedOpp.amount_display}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                Provider: {selectedOpp.provider} · Geographic Scope: {selectedOpp.geographic_eligibility}
              </div>
            </div>

            <div>
              <strong style={{ fontSize: 13 }}>Applicant Eligibility Criteria:</strong>
              <p className="muted" style={{ marginTop: 6, lineHeight: 1.6 }}>{selectedOpp.applicant_eligibility}</p>
            </div>

            <div>
              <strong style={{ fontSize: 13 }}>Application Requirements:</strong>
              <ul style={{ marginTop: 6, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 4 }}>
                {selectedOpp.application_requirements.map((req, i) => (
                  <li key={i} className="muted">{req}</li>
                ))}
              </ul>
            </div>

            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div className="row-between">
                <span className="muted">Official Registry:</span>
                <a href={selectedOpp.official_source_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent-cyan)" }}>
                  Open Portal <ExternalLink size={11} style={{ verticalAlign: "middle" }} />
                </a>
              </div>
              <div className="row-between">
                <span className="muted">Verified At:</span>
                <span className="mono">{new Date(selectedOpp.verified_at).toLocaleString()}</span>
              </div>
              {selectedOpp.provenance_hash && (
                <div className="row-between">
                  <span className="muted">Provenance SHA-256:</span>
                  <span className="mono" style={{ fontSize: 10 }}>{selectedOpp.provenance_hash.slice(0, 16)}...</span>
                </div>
              )}
            </div>

            <div className="row" style={{ gap: 10, marginTop: 10 }}>
              <button
                type="button"
                className="btn"
                style={{ flex: 1 }}
                onClick={() => {
                  handleCreateApplication(selectedOpp.opportunity_id);
                  setSelectedOpp(null);
                }}
              >
                Create Application Workspace
              </button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
