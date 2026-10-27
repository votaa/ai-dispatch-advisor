import { describe, expect, it } from "vitest";
import {
  formatEasternDateTime,
  incidentCreationSource,
  incidentEtrLabel,
  scenarioTemporalState
} from "./scenarioTime";
import type { Incident, ScenarioDescriptor } from "./types";

const base = {
  scenario_id: "timeline_01",
  temporal: {
    kind: "timeline_snapshot" as const,
    as_of_at: "2026-09-28T08:00:00-04:00",
    time_zone: "America/New_York" as const,
    etr_distribution: [{ range: "null", percent: 100 }],
    timeline_id: "timeline",
    snapshot_index: 1,
    snapshot_count: 3,
    assessing_conversion: null,
    assessing_conversion_overrides: {}
  }
} as ScenarioDescriptor;
const second = {
  ...base,
  scenario_id: "timeline_02",
  temporal: { ...base.temporal!, snapshot_index: 2, as_of_at: "2026-09-28T20:00:00-04:00" }
};
const third = {
  ...base,
  scenario_id: "timeline_03",
  temporal: { ...base.temporal!, snapshot_index: 3, as_of_at: "2026-09-29T08:00:00-04:00" }
};

describe("scenario time contract", () => {
  it("formats stored offsets in Eastern time across daylight-saving changes", () => {
    expect(formatEasternDateTime("2026-03-08T06:30:00Z")).toBe("03/08/2026 01:30 EST");
    expect(formatEasternDateTime("2026-03-08T07:30:00Z")).toBe("03/08/2026 03:30 EDT");
    expect(formatEasternDateTime("2026-09-29T22:00:00-04:00")).toBe("09/29/2026 22:00 EDT");
    expect(formatEasternDateTime("2026-09-29T22:00:00")).toBeNull();
  });

  it("distinguishes intentional Assessing Conditions from missing legacy values", () => {
    const incident = { etr: null, etr_status: "assessing_conditions", created_at: null } as Incident;
    expect(incidentEtrLabel(incident)).toBe("Assessing Conditions");
    expect(incidentEtrLabel({ ...incident, etr_status: null, etr: "Unknown" })).toBe("ETR unavailable");
    expect(incidentCreationSource(incident)).toBe("Unavailable");
    expect(incidentCreationSource({ ...incident, created_at: "2026-09-28T08:00:00-04:00", created_at_source: "synthetic_generator" }))
      .toBe("Synthetic scenario generator");
  });

  it("identifies future, stale, and latest eligible timeline snapshots", () => {
    const siblings = [base, second, third];
    const betweenSecondAndThird = Date.parse("2026-09-28T21:00:00-04:00");
    expect(scenarioTemporalState(base, siblings, betweenSecondAndThird)).toMatchObject({
      kind: "stale", suggestedScenario: { scenario_id: "timeline_02" }
    });
    expect(scenarioTemporalState(third, siblings, betweenSecondAndThird)).toMatchObject({
      kind: "future", suggestedScenario: { scenario_id: "timeline_02" }
    });
    expect(scenarioTemporalState(second, siblings, betweenSecondAndThird).kind).toBe("latest");
    expect(scenarioTemporalState(third, siblings, Date.parse("2026-09-29T08:00:00-04:00")).kind).toBe("latest");
  });

  it("withholds timeline guidance when sibling metadata is incomplete or inconsistent", () => {
    expect(scenarioTemporalState(base, [base, second], Date.now()).kind).toBe("unavailable");
    expect(scenarioTemporalState(base, [base, second, {
      ...third,
      temporal: { ...third.temporal, etr_distribution: [{ range: "8h", percent: 100 }] }
    }], Date.now()).kind).toBe("unavailable");
    expect(scenarioTemporalState({
      ...base,
      temporal: { ...base.temporal!, as_of_at: "2026-09-28T09:00:00-04:00" }
    }, [base, second, third], Date.now()).kind).toBe("unavailable");
  });
});
