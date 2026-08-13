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
