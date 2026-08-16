from __future__ import annotations


class EntityNotFoundError(LookupError):
    def __init__(self, entity: str, entity_id: str | None = None) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} not found")


class DecisionReasonRequiredError(ValueError):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"{action.title()} reason is required")


class DecisionConflictError(ValueError):
    def __init__(self, incident_id: str, recommendation_incident_id: str) -> None:
        self.incident_id = incident_id
        self.recommendation_incident_id = recommendation_incident_id
        super().__init__("Recommendation incident does not match the decision incident")


class DecisionCrewSelectionError(ValueError):
    def __init__(self, selected_crew_id: str, message: str) -> None:
        self.selected_crew_id = selected_crew_id
        super().__init__(message)
