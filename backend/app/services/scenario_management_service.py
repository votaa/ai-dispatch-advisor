from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..scenario_service import ScenarioDescriptor, ScenarioService


class ScenarioManagementService:
    def __init__(
        self,
        *,
        data_root: Callable[[], Path],
        active_scenario_id: Callable[[], str],
        set_active_scenario: Callable[[str], None],
    ) -> None:
        self._data_root = data_root
        self._active_scenario_id = active_scenario_id
        self._set_active_scenario = set_active_scenario

    def _service(self) -> ScenarioService:
        return ScenarioService(
            data_root=self._data_root(),
            active_scenario_id=self._active_scenario_id(),
        )

    def list(self) -> list[ScenarioDescriptor]:
        return self._service().list_scenarios()

    def active(self) -> ScenarioDescriptor:
        return self._service().active_scenario()

    def activate(self, scenario_id: str) -> ScenarioDescriptor:
        candidate = self._service().scenario(scenario_id)
        self._set_active_scenario(candidate.scenario_id)
        return self._service().active_scenario()
