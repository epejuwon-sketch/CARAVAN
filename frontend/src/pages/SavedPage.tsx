import React, { useEffect, useState } from "react";
import { Bookmark, Trash2, ArrowRight } from "lucide-react";
import { apiFetch } from "../lib/api";

interface SavedPageProps {
  onNavigate: (route: string) => void;
}

export const SavedPage: React.FC<SavedPageProps> = ({ onNavigate }) => {
  const [savedItems, setSavedItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadSaved() {
    setLoading(true);
    try {
      const res = await apiFetch<any>("/api/v1/saved");
      setSavedItems(res.saved || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSaved();
  }, []);

  async function handleDelete(savedId: string) {
    try {
      await apiFetch(`/api/v1/saved/${savedId}`, { method: "DELETE" });
      loadSaved();
    } catch {
      // ignore
    }
  }

  return (
    <div className="container" style={{ paddingTop: 32, display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="row-between">
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800 }}>Saved Opportunities ({savedItems.length})</h1>
          <p className="muted" style={{ fontSize: 13 }}>
            Bookmarked funding programs for future cycles and review.
          </p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate("discover")}>
          Explore Opportunities
        </button>
      </div>

      {loading ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          Loading saved opportunities...
        </div>
      ) : savedItems.length === 0 ? (
        <div className="card muted" style={{ textAlign: "center", padding: 40 }}>
          No bookmarked opportunities yet. Save items from the Marketplace to review them here.
        </div>
      ) : (
        <div className="grid-2" style={{ gap: 16 }}>
          {savedItems.map((item) => (
            <div key={item.saved_id} className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="row-between">
                <span className="pill pill-cyan">{item.funding_type}</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleDelete(item.saved_id)}
                  title="Remove bookmark"
                >
                  <Trash2 size={13} color="var(--accent-rose)" />
                </button>
              </div>
              <div>
                <strong style={{ fontSize: 16 }}>{item.title}</strong>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{item.provider}</div>
              </div>
              <div className="mono" style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 13 }}>
                {item.amount_display}
              </div>
              <div className="row-between" style={{ marginTop: 4 }}>
                <span className="muted" style={{ fontSize: 11 }}>Saved: {new Date(item.saved_at).toLocaleDateString()}</span>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigate("discover")}
                >
                  View Details <ArrowRight size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
