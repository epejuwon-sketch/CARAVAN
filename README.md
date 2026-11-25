# CARAVAN — Institutional Funding Intelligence, Opportunity Matching & Application Operations Platform

**CARAVAN** is a standalone, customer-facing institutional funding intelligence and opportunity matching platform designed to connect African high-growth enterprises and global ventures with verified non-dilutive grants, concessionary debt, venture capital, and multilateral development facilities.

Zero fabricated opportunities. Cryptographically verified provenance.

---

## Key Capabilities

1. **Funding Intelligence Marketplace**
   - 15 Institutional Funding Categories: Grants, Concessionary Loans, Venture Capital, Angel Syndicates, Pre-Seed/Seed Equity, Accelerators, Prize Competitions, Merit Awards, Working Capital, Equipment Capex Debt, Corporate Venture, Development & DFI Finance, R&D/Science Grants, Philanthropic Foundations, and Fellowships.
   - Filters for Jurisdiction (Nigeria, Pan-African, UK, Global), Sector, Amount, Verification Status, and Deadlines.

2. **Smart Eligibility Matching Engine**
   - Evaluates applicant venture parameters (CAC legal structure, jurisdiction, operating sector, stage, and revenue) against verified program criteria.
   - Detailed match scorecard (0–100%) and criteria score breakdowns.

3. **Governed Application Preparation Workspace**
   - Requirements checklist tracking and stage progression (`DRAFTING`, `DOCS_COLLECTING`, `REVIEW`, `SUBMITTED`, `AWARDED`, `REJECTED`).
   - Secure document metadata organization (Pitch decks, CAC certificates, Audited financials, Tax clearance).
   - Deadline countdown alerts.

4. **Transparent Pricing & Nigerian Payment Gateways**
   - Tiered subscriptions: Free ($0), Starter ($19 / ₦29,000), Growth ($49 / ₦75,000), Pro ($99 / ₦150,000), Institutional ($249 / ₦380,000), and Custom Enterprise.
   - Full webhook fulfillment abstraction for Flutterwave and Paystack sandbox integrations.

5. **AEGIS Security Identity & Tenant Isolation**
   - Full multi-tenant logical isolation and Sentinel RBAC.
   - Zero exposure of internal administrative internals or credentials.
   - Scoped S2S API bridge (`/api/v1/bridge/*`) for authenticated ULTRON Operations.

---

## Architecture

- **Backend:** FastAPI, Python 3.12, SQLAlchemy 2.0, PostgreSQL / SQLite with migration versioning.
- **Frontend:** React 18, TypeScript, Vite, Lucide React, Premium Institutional FinTech Design System.
- **Deployment:** Vercel Serverless ASGI (`api/index.py`) + Static SPA Build (`vercel.json`).

---

## Local Development

### Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest backend/tests
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run build
npm run dev
```

---

## Scoped ULTRON Operations Integration

CARAVAN connects to ULTRON's private operations center via the authenticated header:
`X-Ultron-Bridge-Key: <ULTRON_BRIDGE_API_KEY>`

- Telemetry: `GET /api/v1/bridge/telemetry`
- Sweep Expired Deadlines: `POST /api/v1/bridge/sweep-expired`
