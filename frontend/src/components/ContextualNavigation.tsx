import { ExternalLink, ListFilter, Map as MapIcon } from "lucide-react";
import type { ElementType } from "react";
import type { Crew, Incident } from "../types";

export type OperationalEntityReference =
  | { kind: "incident"; id: string }
  | { kind: "crew"; id: string }
  | { kind: "municipality"; name: string }
  | { kind: "feeder"; id: string }
  | { kind: "critical_facility"; id: string };

export type NavigationDestinationKind = "full_detail" | "related_records" | "show_on_map";

export type OperationalNavigationCommand =
  | { type: "open_incident"; incidentId: string }
  | { type: "open_crew"; crewId: string }
  | { type: "show_on_map"; entityKind: "incident" | "crew"; entityId: string }
  | { type: "filter_incidents"; filter: IncidentNavigationFilter }
  | { type: "filter_crews"; filter: CrewNavigationFilter };

export type IncidentNavigationFilter =
  | { kind: "incident_ids"; ids: string[]; label: string }
  | { kind: "municipality"; value: string; label: string }
  | { kind: "feeder"; value: string; label: string }
  | { kind: "critical_facility"; value: string; label: string };

export type CrewNavigationFilter = {
  kind: "crew_ids";
  ids: string[];
  label: string;
};

export type NavigationDestination = {
  id: string;
  kind: NavigationDestinationKind;
  label: string;
  description: string;
  command: OperationalNavigationCommand;
};

export type NavigationResolverContext = {
  incidents: Incident[];
  crews: Crew[];
  currentView?: "map" | "incidents" | "crews";
  currentEntity?: { kind: "incident" | "crew"; id: string };
};

function isCurrentEntity(
  context: NavigationResolverContext,
  kind: "incident" | "crew",
  id: string
) {
  return context.currentEntity?.kind === kind && context.currentEntity.id === id;
}

export function resolveNavigationDestinations(
  reference: OperationalEntityReference,
  context: NavigationResolverContext
): NavigationDestination[] {
  if (reference.kind === "incident") {
    const incident = context.incidents.find((item) => item.incident_id === reference.id);
    if (!incident) return [];

    const crewIds = Array.from(new Set(incident.assigned_crews
      .map((crew) => crew.crew_id)
      .filter((crewId) => context.crews.some((crew) => crew.crew_id === crewId))));
    const destinations: NavigationDestination[] = [];

    if (!(context.currentView === "incidents" && isCurrentEntity(context, "incident", reference.id))) {
      destinations.push({
        id: `incident-${reference.id}-detail`,
        kind: "full_detail",
        label: "Open incident details",
        description: `Open the authoritative incident record for ${reference.id}.`,
        command: { type: "open_incident", incidentId: reference.id }
      });
    }
    if (crewIds.length) {
      destinations.push({
        id: `incident-${reference.id}-crews`,
        kind: "related_records",
        label: `View assigned crew${crewIds.length === 1 ? "" : "s"} (${crewIds.length})`,
        description: `Open the Crew Board filtered to crews assigned to ${reference.id}.`,
        command: {
          type: "filter_crews",
          filter: { kind: "crew_ids", ids: crewIds, label: `Assigned to ${reference.id}` }
        }
      });
    }
    if (context.currentView !== "map") {
      destinations.push({
        id: `incident-${reference.id}-map`,
        kind: "show_on_map",
        label: "Show on map",
        description: `Select ${reference.id} in Operations Map.`,
        command: { type: "show_on_map", entityKind: "incident", entityId: reference.id }
      });
    }
    return destinations;
  }

  if (reference.kind === "crew") {
    const crew = context.crews.find((item) => item.crew_id === reference.id);
    if (!crew) return [];

    const incidentIds = Array.from(new Set(crew.assigned_incidents
      .map((assignment) => assignment.incident_id)
      .filter((incidentId) => context.incidents.some((incident) => incident.incident_id === incidentId))));
    const destinations: NavigationDestination[] = [];

    if (!(context.currentView === "crews" && isCurrentEntity(context, "crew", reference.id))) {
      destinations.push({
        id: `crew-${reference.id}-detail`,
        kind: "full_detail",
        label: "Open crew details",
        description: `Open the authoritative crew record for ${reference.id}.`,
        command: { type: "open_crew", crewId: reference.id }
      });
    }
    if (incidentIds.length) {
      destinations.push({
        id: `crew-${reference.id}-incidents`,
        kind: "related_records",
        label: `View assigned incident${incidentIds.length === 1 ? "" : "s"} (${incidentIds.length})`,
        description: `Open Incidents filtered to records assigned to ${reference.id}.`,
        command: {
          type: "filter_incidents",
          filter: { kind: "incident_ids", ids: incidentIds, label: `Assigned to ${crew.crew_name} (${reference.id})` }
        }
      });
    }
    if (context.currentView !== "map") {
      destinations.push({
        id: `crew-${reference.id}-map`,
        kind: "show_on_map",
        label: "Show on map",
        description: `Select ${reference.id} in Operations Map.`,
        command: { type: "show_on_map", entityKind: "crew", entityId: reference.id }
      });
    }
    return destinations;
  }

  if (reference.kind === "municipality") {
    const count = context.incidents.filter((incident) => incident.municipality === reference.name).length;
    return count ? [{
      id: `municipality-${reference.name}-incidents`,
      kind: "related_records",
      label: `View ${reference.name} incidents (${count})`,
      description: `Open Incidents filtered to the authoritative municipality value ${reference.name}.`,
      command: {
        type: "filter_incidents",
        filter: { kind: "municipality", value: reference.name, label: `Municipality: ${reference.name}` }
      }
    }] : [];
  }

  if (reference.kind === "feeder") {
    const count = context.incidents.filter((incident) => incident.feeder === reference.id).length;
    return count ? [{
      id: `feeder-${reference.id}-incidents`,
      kind: "related_records",
      label: `View ${reference.id} incidents (${count})`,
      description: `Open Incidents filtered to the authoritative feeder value ${reference.id}.`,
      command: {
        type: "filter_incidents",
        filter: { kind: "feeder", value: reference.id, label: `Feeder: ${reference.id}` }
      }
    }] : [];
  }

  const count = context.incidents.filter(
    (incident) => incident.matched_critical_facility_ids?.includes(reference.id)
  ).length;
  return count ? [{
    id: `critical-facility-${reference.id}-incidents`,
    kind: "related_records",
    label: `View related incidents (${count})`,
    description: `Open Incidents filtered to critical-facility reference ${reference.id}.`,
    command: {
      type: "filter_incidents",
      filter: { kind: "critical_facility", value: reference.id, label: `Critical facility: ${reference.id}` }
    }
  }] : [];
}

const destinationIcons: Record<NavigationDestinationKind, ElementType> = {
  full_detail: ExternalLink,
  related_records: ListFilter,
  show_on_map: MapIcon
};

export function NavigationActions({
  actions,
  accessibleLabel,
  accessibleNameOverrides,
  className = "",
  labelOverrides,
  onNavigate,
  showIcon = true,
  variant = "panel"
}: {
  actions: NavigationDestination[];
  accessibleLabel: string;
  accessibleNameOverrides?: Partial<Record<NavigationDestinationKind, string>>;
  className?: string;
  labelOverrides?: Partial<Record<NavigationDestinationKind, string>>;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  showIcon?: boolean;
  variant?: "panel" | "inline" | "icon";
}) {
  if (!actions.length) return null;

  const actionButtons = actions.map((action) => {
    const Icon = destinationIcons[action.kind];
    const label = labelOverrides?.[action.kind] ?? action.label;
    return (
      <button
        aria-label={variant === "icon" ? accessibleNameOverrides?.[action.kind] ?? action.description : undefined}
        className={variant === "icon" && action.kind === "show_on_map" ? "show-on-map-action" : undefined}
        data-navigation-origin={action.id}
        key={action.id}
        onClick={(event) => {
          event.stopPropagation();
          onNavigate(action.command, event.currentTarget);
        }}
        title={variant === "icon" ? label : action.description}
        type="button"
      >
        {showIcon ? <Icon aria-hidden="true" size={variant === "icon" ? 16 : 15} strokeWidth={2} /> : null}
        {variant === "icon" ? null : <span>{label}</span>}
      </button>
    );
  });
  const actionClassName = `navigation-actions navigation-actions-${variant} ${className}`.trim();

  return variant === "panel" ? (
    <nav aria-label={accessibleLabel} className={actionClassName}>{actionButtons}</nav>
  ) : (
    <span className={actionClassName}>{actionButtons}</span>
  );
}

export function EntityNavigationActions({
  accessibleLabel,
  accessibleNameOverrides,
  context,
  destinationKinds,
  labelOverrides,
  onNavigate,
  reference,
  showIcon = true,
  variant = "inline"
}: {
  accessibleLabel: string;
  accessibleNameOverrides?: Partial<Record<NavigationDestinationKind, string>>;
  context: NavigationResolverContext;
  destinationKinds?: NavigationDestinationKind[];
  labelOverrides?: Partial<Record<NavigationDestinationKind, string>>;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  reference: OperationalEntityReference;
  showIcon?: boolean;
  variant?: "panel" | "inline" | "icon";
}) {
  const actions = resolveNavigationDestinations(reference, context).filter(
    (action) => !destinationKinds || destinationKinds.includes(action.kind)
  );
  return (
    <NavigationActions
      accessibleLabel={accessibleLabel}
      accessibleNameOverrides={accessibleNameOverrides}
      actions={actions}
      labelOverrides={labelOverrides}
      onNavigate={onNavigate}
      showIcon={showIcon}
      variant={variant}
    />
  );
}

export function ContextualNavigationPanel({
  context,
  onNavigate,
  reference
}: {
  context: NavigationResolverContext;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  reference: OperationalEntityReference;
}) {
  const actions = resolveNavigationDestinations(reference, context);
  if (!actions.length) return null;

  return (
    <section className="contextual-navigation" aria-label="Contextual navigation">
      <span className="contextual-navigation-label">Go to</span>
      <NavigationActions
        accessibleLabel="Available destinations"
        actions={actions}
        onNavigate={onNavigate}
      />
    </section>
  );
}
