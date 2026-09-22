export type Incident = {
  incident_id: string;
  region: string;
  municipality: string;
  feeder: string;
  severity: string;
  status: string;
  customers_out: number;
  critical_facility: boolean;
  hazard: string;
  required_skill: string;
  age_minutes: number;
  latitude: number;
  longitude: number;
  etr: string;
  assigned_crews: AssignedCrew[];
  current_decision: RecommendationAction | null;
  critical_facility_level?: 1 | 2 | 3 | null;
  matched_critical_facility_ids?: string[];
  ranking_status?: "ranked" | "withheld";
  ranking_warning?: string | null;
};

export type Crew = {
  crew_id: string;
  crew_name: string;
  home_region: string;
  status: string;
  capability: string;
  current_location: string;
  shift_remaining_hours: number;
  storm_ready: boolean;
  travel_minutes_to_selected_incident: number;
  assigned_incidents: AssignedIncident[];
  map_location?: {
    latitude: number;
    longitude: number;
    village: string;
    reference_id: string;
    precision: "village_center";
  } | null;
  suitability_score?: number;
  capability_match?: boolean;
  estimated_travel_minutes?: number;
};

export type AssignedCrew = {
  crew_id: string;
  crew_name: string;
  assignment_id: string;
  assigned_at: string;
};

export type AssignedIncident = {
  incident_id: string;
  assignment_id: string;
  assigned_at: string;
  municipality: string | null;
  severity: string | null;
};

export type Assignment = {
  assignment_id: string;
  scenario_id: string;
  incident_id: string;
  crew_id: string;
  status: string;
  assigned_at: string;
  notes: string;
};

export type AssignmentReasonCategory =
  | "field_condition_changed"
  | "crew_unavailable"
  | "assignment_entered_in_error"
  | "incident_priority_changed"
  | "supervisor_direction"
  | "other";

export type AssignmentMutation = {
  mutation_id: string;
  scenario_id: string;
  assignment_id: string;
  incident_id: string;
  crew_id: string;
  action: "unassigned" | "reassigned";
  reason: string;
  reason_category: AssignmentReasonCategory;
  note?: string | null;
  actor: string;
  created_at: string;
  new_assignment_id?: string | null;
  new_crew_id?: string | null;
};

export type DashboardSummary = {
  active_incidents: number;
  customers_out: number;
  available_crews: number;
  assigned_crews: number;
  critical_facility_incidents: number;
  high_priority_incidents: number;
  top_incidents: Incident[];
  scenario: string;
  data_freshness: string;
};

export type CopilotEvidence = {
  source_type:
    | "dashboard"
    | "incident"
    | "crew"
    | "recommendation"
    | "critical_facility"
    | "geography"
    | "travel_estimate"
    | "pseg_reference";
  record_id: string;
  label: string;
};

export type CopilotResponse = {
  answer: string;
  intent: string;
  source: string;
  safety_note: string;
  execution_mode: "local_query" | "llm_grounded" | "rule_based_fallback";
  scenario_id: string;
  generated_at: string;
  request_time?: {
    received_at: string;
    timezone: "UTC";
    source: "backend_server_clock";
    clock_skew: "not_measured";
  } | null;
  data_snapshot_at: string | null;
  provider: string | null;
  model: string | null;
  warning: string | null;
  response_scope?: string | null;
  evidence: CopilotEvidence[];
};

export type ScenarioEventType = "blue_sky" | "storm" | "crew_shortage" | "critical_facility";

export type ScenarioFreshness = {
  updated_at: string;
  source: "scenario_generation" | "file_upload" | "repository_publish" | "scenario_update";
  provenance: string;
};

export type ScenarioDescriptor = {
  schema_version: "1.0";
  scenario_id: string;
  name: string;
  description: string;
  event_type: ScenarioEventType;
  freshness: ScenarioFreshness | null;
  expected_conditions: string[];
  files: {
    incidents: string;
    crews: string;
    assignments: string;
    historical_repairs: string;
    weather: string;
    critical_facilities: string;
    topology: string;
  };
  validation_status: "valid";
  is_active: boolean;
};

export type Recommendation = {
  recommendation_id: string;
  incident_id: string;
  recommended_action: string;
  recommended_crew: Crew | null;
  confidence: string;
  expected_impact: string;
  factors: string[];
  constraints: string[];
  alternatives: Crew[];
  explanation?: RecommendationExplanation | null;
};

export type RecommendationExplanation = {
  confidence_rationale: {
    score: number | null;
    threshold: number | null;
    reason: string;
  };
  factors: Array<{
    factor_id: string;
    description: string;
    contribution: number | null;
    evidence: string | null;
  }>;
  constraints: Array<{
    constraint_id: string;
    status: "satisfied" | "not_satisfied";
    description: string;
  }>;
  excluded_candidates: Array<{ crew_id: string; reasons: string[] }>;
  assumptions: string[];
  data_quality_warnings: string[];
  algorithm_version: string;
  policy_version: string;
};

export type RecommendationActionType = "accepted" | "modified" | "deferred" | "overridden";

export type RecommendationAction = {
  event_id: string;
  scenario_id: string;
  recommendation_id: string;
  incident_id: string;
  crew_id: string | null;
  action: RecommendationActionType;
  reason: string | null;
  note: string | null;
  recommendation: Recommendation;
  created_at: string;
  actor: string;
};
