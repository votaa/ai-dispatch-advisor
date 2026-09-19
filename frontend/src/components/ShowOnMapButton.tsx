import { Map as MapIcon } from "lucide-react";

export type MapEntityKind = "incident" | "crew";

export function ShowOnMapButton({
  entityId,
  entityKind,
  onShowOnMap
}: {
  entityId: string;
  entityKind: MapEntityKind;
  onShowOnMap: (entityKind: MapEntityKind, entityId: string) => void;
}) {
  return (
    <button
      aria-label={`Show ${entityKind} ${entityId} on map`}
      className="show-on-map-action"
      onClick={(event) => {
        event.stopPropagation();
        onShowOnMap(entityKind, entityId);
      }}
      title="Show on map"
      type="button"
    >
      <MapIcon aria-hidden="true" size={16} strokeWidth={2} />
    </button>
  );
}
