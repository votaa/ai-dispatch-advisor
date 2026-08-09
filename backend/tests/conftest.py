from pathlib import Path

import pytest

from app import data_loader, decision_store


@pytest.fixture(autouse=True)
def isolate_runtime_state(tmp_path: Path, monkeypatch):
    original_scenario = data_loader.get_active_scenario()
    data_loader.set_active_scenario("base")
    monkeypatch.setattr(decision_store, "DB_PATH", tmp_path / "aida-test-decisions.db")
    yield
    data_loader.set_active_scenario(original_scenario)
