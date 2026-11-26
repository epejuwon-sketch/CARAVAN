import React, { useState } from "react";
import {
  ShieldCheck,
  Lock,
  Globe,
  FileText,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  ArrowLeft,
  Mail,
  Building,
} from "lucide-react";

interface LegalPageProps {
  onNavigate: (route: string) => void;
}

export const PrivacyPolicyPage: React.FC<LegalPageProps> = ({ onNavigate }) => {
  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, maxWidth: 880, display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          className="row muted"
          style={{ gap: 6, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onNavigate("home")}
        >
          <ArrowLeft size={14} /> Back to Overview
        </button>
        <span className="pill pill-gold" style={{ alignSelf: "flex-start", marginTop: 8 }}>Statutory Regulatory Compliance</span>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>CARAVAN Global Privacy Policy</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Effective Date: November 26, 2026 &middot; Version 1.0 &middot; Compliance: Nigeria Data Protection Act (NDPA 2023) &amp; GDPR
        </p>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 24, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>1. Introduction &amp; Data Controller Scope</h2>
          <p>
            CARAVAN (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;) operates an institutional funding intelligence, opportunity matching, and application operations platform. We are committed to protecting the privacy, confidentiality, and data sovereignty of founders, enterprises, and capital seekers accessing our platform.
          </p>
          <p>
            This Privacy Policy explains how we collect, process, store, and safeguard personal and proprietary business data in compliance with the <strong>Nigeria Data Protection Act 2023 (NDPA)</strong>, General Data Protection Regulation (GDPR), and applicable international standards.
          </p>
          <div className="list-item" style={{ fontSize: 13 }}>
            <strong>Data Controller Identity:</strong> CARAVAN Capital Intelligence Ltd. [Pending Owner Legal Corporate Registration Confirmation]<br />
            <strong>Operating Hub:</strong> Central Business District, Abuja (FCT), Nigeria<br />
            <strong>Data Protection Contact:</strong> <span className="mono gold-text">dpo@caravanfunding.com</span>
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>2. Categories of Information Collected</h2>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <li>
              <strong>Account &amp; Identity Data:</strong> Full name, verified business email address, professional title, cryptographic password hash (Argon2id), and authentication tokens.
            </li>
            <li>
              <strong>Corporate Entity Records:</strong> Registered business name, CAC registration number, jurisdiction of incorporation, state location, operating sector, enterprise stage, annual turnover, and employee count.
            </li>
            <li>
              <strong>Application Materials &amp; Pitch Assets:</strong> Uploaded executive summaries, pitch decks, audited financial statements, tax clearance certificates, and proposal narratives.
            </li>
            <li>
              <strong>AURELIA Intelligence Interaction Data:</strong> Search queries, prompt directives, application drafting requests, and feedback provided to the AURELIA funding assistant.
            </li>
            <li>
              <strong>Billing &amp; Payment Records:</strong> Payment gateway transaction references (Flutterwave and Paystack), subscription tier, currency, and renewal dates. <em>Note: CARAVAN never stores, processes, or retains raw credit/debit card numbers (PAN) or CVVs.</em>
            </li>
            <li>
              <strong>Technical &amp; Telemetry Data:</strong> IP address, device type, browser user agent, session timestamps, and audit access logs.
            </li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>3. Legal Bases for Processing (NDPA &amp; GDPR)</h2>
          <p>We process your data strictly under recognized lawful bases:</p>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <li><strong>Contractual Necessity:</strong> To fulfill our service agreement, perform opportunity matching, and generate application workspaces.</li>
            <li><strong>Legitimate Interests:</strong> To prevent platform abuse, conduct malware scanning on uploaded documents, and enforce multi-tenant isolation.</li>
            <li><strong>Legal &amp; Statutory Obligations:</strong> To maintain audit trails and tax/billing transaction records in accordance with CAMA 2020.</li>
            <li><strong>Explicit Consent:</strong> For optional marketing digests and market intelligence updates, which you may withdraw at any time.</li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>4. Third-Party Data Processors</h2>
          <p>We share minimal, strictly scoped data with vetted infrastructure partners under strict confidentiality agreements:</p>
          <div className="table-responsive">
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                  <th style={{ padding: "8px 0" }}>Processor</th>
                  <th style={{ padding: "8px 0" }}>Purpose</th>
                  <th style={{ padding: "8px 0" }}>Location</th>
                  <th style={{ padding: "8px 0" }}>Data Shared</th>
                </tr>
              </thead>
              <tbody className="muted">
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><strong>Google Gemini</strong></td>
                  <td>AURELIA AI proposal analysis &amp; synthesis</td>
                  <td>United States / Global</td>
                  <td>Prompt context (zero model training on inputs)</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><strong>Supabase / AWS</strong></td>
                  <td>PostgreSQL primary encrypted storage</td>
                  <td>Dublin, EU (eu-west-1)</td>
                  <td>Encrypted database records &amp; documents</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><strong>Flutterwave &amp; Paystack</strong></td>
                  <td>PCI-DSS compliant payment processing</td>
                  <td>Nigeria &amp; Global</td>
                  <td>Transaction references &amp; billing amounts</td>
                </tr>
                <tr>
                  <td style={{ padding: "8px 0" }}><strong>Vercel Edge Network</strong></td>
                  <td>Serverless runtime &amp; global CDN</td>
                  <td>Global Edge</td>
                  <td>Encrypted HTTP traffic &amp; IP telemetry</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>5. Data Security &amp; Encryption Standards</h2>
          <p>
            All data in transit is protected using <strong>TLS 1.3</strong> with HTTP Strict Transport Security (HSTS). All document vaults and PostgreSQL database instances employ <strong>AES-256</strong> encryption at rest. Every uploaded document is routed through an automated heuristic and magic-byte malware scanner before storage in private, authorization-gated tenant buckets.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>6. Data Subject Rights &amp; Self-Service Deletion</h2>
          <p>Under the NDPA 2023 and GDPR, you have the following enforceable rights:</p>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <li><strong>Right to Access &amp; Portability:</strong> You can export your full platform profile, application files, and history at any time via <code>/api/v1/account/export-data</code>.</li>
            <li><strong>Right to Erasure (Deletion):</strong> You can initiate self-service account deactivation and document purging via the Account settings or <code>DELETE /api/v1/account</code>.</li>
            <li><strong>Right to Rectification:</strong> You can update organization parameters and profile records in real-time.</li>
            <li><strong>Right to Withdraw Consent:</strong> One-click unsubscribe is available for marketing communications at <code>/api/v1/notifications/unsubscribe</code>.</li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>7. Supervisory Authority Complaints</h2>
          <p>
            If you believe your personal data has been handled inconsistently with the NDPA 2023, you have the statutory right to lodge a complaint with the <strong>Nigeria Data Protection Commission (NDPC)</strong> at <code>info@ndpc.gov.ng</code>.
          </p>
        </section>
      </div>
    </div>
  );
};

export const TermsOfServicePage: React.FC<LegalPageProps> = ({ onNavigate }) => {
  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, maxWidth: 880, display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          className="row muted"
          style={{ gap: 6, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onNavigate("home")}
        >
          <ArrowLeft size={14} /> Back to Overview
        </button>
        <span className="pill pill-gold" style={{ alignSelf: "flex-start", marginTop: 8 }}>Institutional Service Agreement</span>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>CARAVAN Terms of Service</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Effective Date: November 26, 2026 &middot; Version 1.0 &middot; Governing Law: Federal Republic of Nigeria
        </p>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 24, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>1. Agreement to Terms &amp; Age Eligibility</h2>
          <p>
            By accessing or using the CARAVAN platform (&ldquo;Platform&rdquo;), you confirm that you are at least <strong>18 years of age</strong> (or the age of majority in your jurisdiction) and possess full corporate and legal authority to bind your organization to these Terms. If you do not agree to these Terms, you must not access or use the Platform.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>2. ZERO FUNDING GUARANTEE &amp; DISCLAIMER OF AWARDS</h2>
          <div className="card" style={{ borderLeft: "4px solid var(--accent-gold-bright)", backgroundColor: "var(--bg-secondary)" }}>
            <strong style={{ color: "#FFFFFF" }}>IMPORTANT STATUTORY NOTICE:</strong>
            <p style={{ marginTop: 6, fontSize: 13 }}>
              CARAVAN IS AN INDEPENDENT CAPITAL INTELLIGENCE, MATCHING, AND PROPOSAL ASSISTANCE PLATFORM. <strong>CARAVAN IS NOT A GRANTMAKER, LENDER, VENTURE CAPITAL FUND, OR FINANCIAL UNDERWRITER.</strong> CARAVAN DOES NOT GUARANTEE THAT ANY APPLICATION WILL BE APPROVED, FUNDED, DISBURSED, OR AWARDED. ALL FUNDING DECISIONS, SELECTION CRITERIA, CRITERIA WEIGHTINGS, AND DISBURSEMENTS ARE SOLELY DETERMINED BY THIRD-PARTY INSTITUTIONAL PROVIDERS.
            </p>
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>3. AURELIA AI Funding Intelligence Assistant</h2>
          <p>
            CARAVAN provides AURELIA, an artificial intelligence assistant designed to help founders identify opportunities, analyze eligibility gaps, and draft proposals. You acknowledge and agree that:
          </p>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <li>AURELIA provides advisory drafting assistance and automated synthesis, not legal, accounting, or binding financial advice.</li>
            <li>You are solely responsible for reviewing all proposals, verifying factual statements, and ensuring submission accuracy before external transmission.</li>
            <li>External submissions through official portals require explicit customer authorization. CARAVAN will never submit binding commitments without your approval.</li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>4. Customer Intellectual Property Rights</h2>
          <p>
            You retain <strong>100% full and unencumbered ownership</strong> of all proprietary materials, pitch decks, business plans, financial models, and corporate secrets uploaded to your workspace. We claim no ownership, patent, copyright, or trademark over your venture data.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>5. Subscription Billing &amp; Renewals</h2>
          <p>
            CARAVAN offers tiered subscription plans (Free, Starter, Growth, Pro, and Institutional). Paid subscriptions renew automatically on a monthly or annual billing cycle until cancelled. You may cancel your subscription at any time via the Billing tab; cancellation takes effect at the expiration of your current prepaid billing term.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>6. Prohibited Activities</h2>
          <p>You agree not to:</p>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <li>Upload fraudulent CAC certificates, forged financial records, or intentionally misleading data.</li>
            <li>Attempt to bypass multi-tenant isolation, conduct IDOR attacks, or access another organization&rsquo;s data.</li>
            <li>Upload executable malware, viruses, or malicious scripts.</li>
            <li>Reverse engineer or scrape CARAVAN&rsquo;s proprietary opportunity matching algorithms without written authorization.</li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>7. Governing Law &amp; Dispute Resolution</h2>
          <p>
            These Terms shall be governed by and construed in accordance with the <strong>Laws of the Federal Republic of Nigeria</strong>. Any dispute arising out of or in connection with these Terms shall be resolved through binding arbitration in Abuja, Nigeria, under the Arbitration and Mediation Act 2023.
          </p>
        </section>
      </div>
    </div>
  );
};

export const RefundPolicyPage: React.FC<LegalPageProps> = ({ onNavigate }) => {
  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, maxWidth: 880, display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          className="row muted"
          style={{ gap: 6, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onNavigate("home")}
        >
          <ArrowLeft size={14} /> Back to Overview
        </button>
        <span className="pill pill-gold" style={{ alignSelf: "flex-start", marginTop: 8 }}>Consumer &amp; Enterprise Protection</span>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>CARAVAN Refund &amp; Cancellation Policy</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Effective Date: November 26, 2026 &middot; Version 1.0 &middot; Transparent Billing Architecture
        </p>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 24, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>1. Cancellation Policy</h2>
          <p>
            You can cancel your CARAVAN subscription at any time directly through the <strong>Billing</strong> tab in your dashboard. Upon cancellation:
          </p>
          <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <li>Your plan entitlements remain fully active until the end of the paid billing period.</li>
            <li>No further automated recurring charges will be initiated against your Flutterwave or Paystack authorization.</li>
            <li>At period expiry, your account automatically transitions to the permanent Free tier without losing historical application records.</li>
          </ul>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>2. 7-Day Satisfaction Guarantee (Annual Subscriptions)</h2>
          <p>
            For first-time annual subscription purchases, CARAVAN provides a <strong>7-day cooling-off guarantee</strong>. If you determine within 7 calendar days of your initial annual charge that CARAVAN does not meet your institutional capital requirements, you may request a 100% full refund by contacting <span className="mono gold-text">billing@caravanfunding.com</span>.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>3. Monthly Subscriptions &amp; Mid-Cycle Inquiries</h2>
          <p>
            Monthly subscription charges are non-refundable once the billing cycle begins. We do not provide prorated refunds for partial month usage, but you maintain full platform access for the remaining days of your monthly cycle.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>4. Processing Timeframes</h2>
          <p>
            Approved refunds are remitted to the original payment method via Paystack or Flutterwave within <strong>5 to 10 business days</strong>, depending on your financial institution&rsquo;s clearing cycle.
          </p>
        </section>
      </div>
    </div>
  );
};

export const CookiePolicyPage: React.FC<LegalPageProps> = ({ onNavigate }) => {
  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, maxWidth: 880, display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          className="row muted"
          style={{ gap: 6, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onNavigate("home")}
        >
          <ArrowLeft size={14} /> Back to Overview
        </button>
        <span className="pill pill-gold" style={{ alignSelf: "flex-start", marginTop: 8 }}>Tracking Transparency</span>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>CARAVAN Cookie &amp; Storage Policy</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Effective Date: November 26, 2026 &middot; Version 1.0 &middot; Minimal Tracking Architecture
        </p>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 24, lineHeight: 1.7, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>1. How We Use Cookies &amp; Local Storage</h2>
          <p>
            CARAVAN uses strictly minimal client storage technologies (Cookies and browser <code>localStorage</code>) to maintain security, session state, and user preferences. We operate on a privacy-first principle: <strong>Zero cross-site advertising or third-party behavioral tracking cookies</strong> are placed on your device.
          </p>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>2. Storage Key Inventory</h2>
          <div className="table-responsive">
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                  <th style={{ padding: "8px 0" }}>Key Name</th>
                  <th style={{ padding: "8px 0" }}>Classification</th>
                  <th style={{ padding: "8px 0" }}>Lifespan</th>
                  <th style={{ padding: "8px 0" }}>Purpose</th>
                </tr>
              </thead>
              <tbody className="muted">
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><code>caravan_token</code></td>
                  <td>Strictly Essential</td>
                  <td>Session / 24h</td>
                  <td>Holds cryptographic JWT bearer token for API authentication</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><code>caravan_cookie_consent</code></td>
                  <td>Strictly Essential</td>
                  <td>365 Days</td>
                  <td>Remembers your cookie banner preferences and opt-ins</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 0" }}><code>cf_clearance</code></td>
                  <td>Security</td>
                  <td>Cloudflare Managed</td>
                  <td>Bot mitigation and Cloudflare Turnstile human challenge validation</td>
                </tr>
                <tr>
                  <td style={{ padding: "8px 0" }}><code>caravan_ui_filters</code></td>
                  <td>Functional</td>
                  <td>Persistent</td>
                  <td>Saves marketplace search filters and sector preferences</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={{ fontSize: 18, color: "var(--accent-gold-bright)", fontWeight: 700 }}>3. Managing Your Preferences</h2>
          <p>
            You can modify your cookie choices at any time using the &ldquo;Cookie Preferences&rdquo; action in the footer or by clearing your browser cache. Essential cookies cannot be disabled as they are technically necessary to log in and use CARAVAN securely.
          </p>
        </section>
      </div>
    </div>
  );
};

export const BusinessOperatorPage: React.FC<LegalPageProps> = ({ onNavigate }) => {
  return (
    <div className="container" style={{ paddingTop: 40, paddingBottom: 60, maxWidth: 880, display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          className="row muted"
          style={{ gap: 6, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={() => onNavigate("home")}
        >
          <ArrowLeft size={14} /> Back to Overview
        </button>
        <span className="pill pill-gold" style={{ alignSelf: "flex-start", marginTop: 8 }}>Corporate Transparency</span>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#FFFFFF" }}>Business &amp; Operator Information</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Statutory Disclosures &middot; Corporate Governance &middot; Institutional Contacts
        </p>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 20, fontSize: 14, backgroundColor: "var(--bg-card)" }}>
        <div className="row" style={{ gap: 12 }}>
          <Building size={20} color="var(--accent-gold-bright)" />
          <div>
            <strong style={{ fontSize: 16, color: "#FFFFFF" }}>Operating Entity:</strong>
            <div className="muted" style={{ marginTop: 2 }}>
              CARAVAN Capital Intelligence Ltd. <span className="pill pill-gold mono" style={{ fontSize: 11 }}>Pending Owner Confirmation</span>
            </div>
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="row-between">
            <span className="muted">Principal Operating Office (Nigeria):</span>
            <strong style={{ color: "#FFFFFF" }}>Central Business District, Abuja, Federal Capital Territory, Nigeria</strong>
          </div>
          <div className="row-between">
            <span className="muted">Expansion Liaison Hub (United Kingdom):</span>
            <strong style={{ color: "#FFFFFF" }}>Mayfair / City of London, United Kingdom [Target 2027]</strong>
          </div>
          <div className="row-between">
            <span className="muted">Corporate Registration Authority:</span>
            <span>Corporate Affairs Commission (CAC), Nigeria [RC Number: Pending Confirmation]</span>
          </div>
          <div className="row-between">
            <span className="muted">Institutional &amp; DFI Partnerships:</span>
            <span className="mono gold-text">institutions@caravanfunding.com</span>
          </div>
          <div className="row-between">
            <span className="muted">General Customer Support:</span>
            <span className="mono gold-text">support@caravanfunding.com</span>
          </div>
          <div className="row-between">
            <span className="muted">Data Protection Officer:</span>
            <span className="mono gold-text">dpo@caravanfunding.com</span>
          </div>
        </div>

        <div className="card" style={{ backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border-gold)", marginTop: 8 }}>
          <strong style={{ color: "var(--accent-gold-bright)", fontSize: 13 }}>Owner Confirmation Note:</strong>
          <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Official certificate of incorporation (RC Number) and registered Nigerian office address details are subject to final platform owner confirmation prior to full public commercial launch.
          </p>
        </div>
      </div>
    </div>
  );
};
