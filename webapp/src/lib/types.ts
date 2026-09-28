/**
 * AG-UI types — subset of the AG-UI event schema we use.
 */
export type AgUiEventType =
  | "CONNECTED"
  | "RUN_STARTED"
  | "TEXT_MESSAGE_START"
  | "TEXT_MESSAGE_CONTENT"
  | "TEXT_MESSAGE_END"
  | "TOOL_CALL_START"
  | "TOOL_CALL_END"
  | "STATE_SNAPSHOT"
  | "RUN_FINISHED"
  | "RUN_ERROR";

export interface AgUiEvent {
  type: AgUiEventType;
  timestamp?: string;
  run_id?: string;
  // TEXT_MESSAGE_*
  message_id?: string;
  delta?: string;
  // TOOL_CALL_*
  tool_call_id?: string;
  tool_name?: string;
  tool_call_type?: "function" | "client";
  args?: Record<string, unknown>;
  // STATE_SNAPSHOT
  snapshot?: WorkflowState;
  // RUN_FINISHED / RUN_ERROR
  status?: string;
  error?: string;
}

export interface Offer {
  id: string;
  title: string;
  description: string;
  category: "merchandise" | "food_beverage";
  offer_type: "percentage_discount" | "fixed_amount";
  value: string;
  offer_code: string;
  justification: string;
  incident_alert?: string | null;
}

export interface FanProfile {
  fanId: string;
  fanName: string;
  loyaltyTier: string;
  preferredSectionId: string;
  baseEngagementScore: number;
  lastOfferDaysAgo: number;
  offerFatigued: boolean;
}

export type BreakType = string;

export interface TriggeredFan extends FanProfile {
  currentEngagementScore: number;
  engagementDropAmount: number;
  triggerThreshold: number;
  triggerReason: string;
  quarter: number | null;
  gameMinute: number | null;
  churnRiskScore: number;
}

export interface GameEventResponse {
  break_type: BreakType;
  break_label: string;
  game_id: string;
  triggered_fans: TriggeredFan[];
}

export interface RecentOffer {
  promoId: string;
  offerTimestamp: string;
  offerCategory: string;
  offerType: string;
  offerValue: number;
  channel: string;
  triggerContext: string;
  outcome: string;
  revenueImpact: number;
  promoResponseRate: number;
}

export interface FanDetail {
  fanId: string;
  fanName: string;
  loyaltyTier: string;
  preferredSectionId: string;
  avgSpendPerGame: number;
  avgConcessionSpend: number;
  avgMerchandiseSpend: number;
  baseEngagementScore: number;
  churnRiskScore: number;
  offerFatigueGapMinutes: number;
  recentOffers: RecentOffer[];
}


export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export type RedemptionStepName = "scanning" | "eventhouse" | "lakehouse" | "complete";
export type RedemptionStepStatus = "idle" | "running" | "done" | "error";

export interface RedemptionStep {
  name: RedemptionStepName;
  label: string;
  status: RedemptionStepStatus;
  message: string;
  latency_ms?: number;
}

export interface RedemptionResult {
  transaction_id?: string;
  revenue_impact?: number;
  suggested_question?: string;
}


export interface ApprovalDecision {
  approved: boolean;
  reason: string;
  decided_at: string;
}

export interface WorkflowState {
  run_id?: string;
  fan_id?: string;
  game_id?: string;
  workflow_status?:
    | "starting"
    | "started"
    | "awaiting_approval"
    | "completed"
    | "suppressed";
  offers?: Offer[];
  decisions?: Record<string, ApprovalDecision>;
}
