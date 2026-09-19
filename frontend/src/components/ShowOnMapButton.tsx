import {
  NavigationActions,
  resolveNavigationDestinations
} from "./ContextualNavigation";
import type {
  NavigationResolverContext,
  OperationalNavigationCommand
} from "./ContextualNavigation";

export type MapEntityKind = "incident" | "crew";

export function ShowOnMapButton({
  entityId,
  entityKind,
  navigationContext,
  onNavigate
}: {
  entityId: string;
  entityKind: MapEntityKind;
  navigationContext: NavigationResolverContext;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
}) {
  const actions = resolveNavigationDestinations(
    { kind: entityKind, id: entityId },
    navigationContext
  ).filter((action) => action.kind === "show_on_map");

  return (
    <NavigationActions
      accessibleLabel={`${entityKind} ${entityId} map destination`}
      accessibleNameOverrides={{ show_on_map: `Show ${entityKind} ${entityId} on map` }}
      actions={actions}
      labelOverrides={{ show_on_map: "Show on map" }}
      onNavigate={onNavigate}
      variant="icon"
    />
  );
}
