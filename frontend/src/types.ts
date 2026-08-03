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
};

export type Assignment = {
  assignment_id: string;
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

export type Recommendation = {
  incident_id: string;
  recommended_action: string;
  recommended_crew: Crew | null;
  confidence: string;
  expected_impact: string;
  factors: string[];
  constraints: string[];
  alternatives: Crew[];
};

