import type { Incident, ScenarioDescriptor } from "./types";

type TemporalStateKind = "legacy" | "latest" | "future" | "stale" | "unavailable";

export type ScenarioTemporalState = {
  kind: TemporalStateKind;
  suggestedScenario?: ScenarioDescriptor;
};

export function parseAwareInstant(value?: string | null): number | null {
  if (!value || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function formatEasternDateTime(value?: string | null): string | null {
  const timestamp = parseAwareInstant(value);
  if (timestamp === null) return null;
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
    year: "numeric"
  }).formatToParts(timestamp);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("month")}/${part("day")}/${part("year")} ${part("hour")}:${part("minute")} ${part("timeZoneName")}`;
}

export function incidentEtrLabel(incident: Incident): string {
  if (incident.etr_status === "assessing_conditions") return "Assessing Conditions";
  return formatEasternDateTime(incident.etr) ?? "ETR unavailable";
}

export function incidentCreationSource(incident: Incident): string {
  if (!formatEasternDateTime(incident.created_at)) return "Unavailable";
  if (incident.created_at_source === "synthetic_generator") return "Synthetic scenario generator";
  if (incident.created_at_source === "source_record") return "Source record";
  return "Unavailable";
}

export function scenarioTemporalState(
  selected: ScenarioDescriptor | null,
  scenarios: ScenarioDescriptor[],
  now: number
): ScenarioTemporalState {
  const temporal = selected?.temporal;
  if (!temporal) return { kind: "legacy" };
  const selectedCutoff = parseAwareInstant(temporal.as_of_at);
  if (selectedCutoff === null) return { kind: "unavailable" };
  if (temporal.kind === "single_snapshot") {
    return { kind: selectedCutoff > now ? "future" : "latest" };
  }
  if (!temporal.timeline_id || !temporal.snapshot_count || !temporal.snapshot_index) {
    return { kind: "unavailable" };
  }
  const siblings = scenarios.filter((scenario) =>
    scenario.temporal?.kind === "timeline_snapshot" &&
    scenario.temporal.timeline_id === temporal.timeline_id
  );
  if (siblings.length !== temporal.snapshot_count) return { kind: "unavailable" };
  const ordered = [...siblings].sort((left, right) =>
    (left.temporal?.snapshot_index ?? 0) - (right.temporal?.snapshot_index ?? 0)
  );
  const policy = JSON.stringify({
    distribution: temporal.etr_distribution,
    conversion: temporal.assessing_conversion ?? null,
    overrides: temporal.assessing_conversion_overrides ?? {},
    timeZone: temporal.time_zone
  });
  let previousCutoff = -Infinity;
  for (const [index, sibling] of ordered.entries()) {
    const item = sibling.temporal;
    const cutoff = parseAwareInstant(item?.as_of_at);
    const siblingPolicy = JSON.stringify({
      distribution: item?.etr_distribution,
      conversion: item?.assessing_conversion ?? null,
      overrides: item?.assessing_conversion_overrides ?? {},
      timeZone: item?.time_zone
    });
    if (
      !item || item.snapshot_index !== index + 1 || item.snapshot_count !== ordered.length ||
      cutoff === null || cutoff <= previousCutoff || siblingPolicy !== policy
    ) return { kind: "unavailable" };
    previousCutoff = cutoff;
  }
  const listedSelected = ordered.find((scenario) => scenario.scenario_id === selected?.scenario_id);
  if (
    !listedSelected ||
    listedSelected.temporal?.snapshot_index !== temporal.snapshot_index ||
    parseAwareInstant(listedSelected.temporal?.as_of_at) !== selectedCutoff
  ) {
    return { kind: "unavailable" };
  }
  const latestEligible = [...ordered].reverse().find((scenario) =>
    (parseAwareInstant(scenario.temporal?.as_of_at) ?? Infinity) <= now
  );
  if (selectedCutoff > now) {
    return { kind: "future", suggestedScenario: latestEligible };
  }
  if (latestEligible && latestEligible.scenario_id !== selected?.scenario_id) {
    return { kind: "stale", suggestedScenario: latestEligible };
  }
  return { kind: "latest" };
}
