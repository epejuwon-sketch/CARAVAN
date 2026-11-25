export type FundingType =
  | "GRANT"
  | "LOAN"
  | "VENTURE_CAPITAL"
  | "ANGEL_INVESTMENT"
  | "SEED_FUNDING"
  | "ACCELERATOR"
  | "COMPETITION"
  | "AWARD"
  | "WORKING_CAPITAL"
  | "EQUIPMENT_FINANCING"
  | "CORPORATE_FUNDING"
  | "INSTITUTIONAL_FINANCE"
  | "RESEARCH_FUNDING"
  | "PHILANTHROPIC_FUNDING"
  | "SCHOLARSHIP";

export interface FundingOpportunity {
  opportunity_id: string;
  title: string;
  provider: string;
  funding_type: FundingType;
  amount_min?: number;
  amount_max?: number;
  currency: string;
  amount_display: string;
  geographic_eligibility: string;
  applicant_eligibility: string;
  industry_sector: string;
  application_requirements: string[];
  opening_date?: string;
  deadline_at?: string;
  is_rolling: boolean;
  official_source_url: string;
  verification_status: "VERIFIED" | "UNVERIFIED" | "EXPIRED" | "CLOSED";
  verified_at: string;
  source_name: string;
  provenance_hash?: string;
}

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  role: "CUSTOMER" | "ADMIN";
  organization_id: string;
  organization_name: string;
}

export interface Organization {
  org_id: string;
  name: string;
  entity_type: string;
  country: string;
  state_location: string;
  sector: string;
  stage: string;
  annual_revenue_usd: number;
  funding_goals: string;
  team_size: number;
  team_members: Array<{
    user_id: string;
    email: string;
    full_name: string;
    role: string;
  }>;
}

export interface Application {
  application_id: string;
  organization_id: string;
  opportunity_id: string;
  opportunity_title: string;
  provider: string;
  funding_type: string;
  status: "DRAFTING" | "DOCS_COLLECTING" | "REVIEW" | "SUBMITTED" | "AWARDED" | "REJECTED";
  checklist_progress: Array<{ item: string; completed: boolean }>;
  deadline_at?: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface EligibilityAssessment {
  assessment_id: string;
  organization_id: string;
  opportunity_id: string;
  opportunity_title: string;
  provider: string;
  match_score: number;
  recommendation_level: "STRONG" | "MODERATE" | "WEAK" | "INELIGIBLE";
  criteria_breakdown: Record<string, { matched: boolean | string; score: number; reason: string }>;
}

export interface Subscription {
  subscription_id: string;
  organization_id: string;
  tier: "FREE" | "STARTER" | "GROWTH" | "PRO" | "INSTITUTIONAL" | "CUSTOM";
  tier_name: string;
  price_usd: number;
  price_ngn: number;
  status: "ACTIVE" | "PAST_DUE" | "CANCELED";
  billing_provider: string;
  renewal_date?: string;
  features: string[];
}
