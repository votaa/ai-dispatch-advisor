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

export type ScenarioEventType = "blue_sky" | "storm" | "crew_shortage" | "critical_facility";

export type ScenarioDescriptor = {
  schema_version: "1.0";
  scenario_id: string;
  name: string;
  description: string;
  event_type: ScenarioEventType;
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
