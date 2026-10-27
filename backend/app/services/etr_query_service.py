from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from ..api_models import ETRAnalysis, ETRCategoryCounts, ETRExample
from ..domain.models import Incident
from ..scenario_service import ScenarioDescriptor


ETRMode = Literal["current", "scenario_preview"]
EASTERN = ZoneInfo("America/New_York")
GRACE_MINUTES = 10
SOON_MINUTES = 60
CATEGORIES = ("expired", "due_now", "due_soon", "valid_future", "unavailable")


def is_etr_count_question(message: str) -> bool:
    text = re.sub(r"[^a-z0-9]+", " ", message.casefold()).strip()
    etr_subject = bool(re.search(r"\b(?:etrs?|estimated restoration times?|restoration estimates?)\b", text))
    timing = bool(re.search(r"\b(?:expired|due now|due soon|due within|coming due|past due|overdue|valid future|assessing conditions)\b", text))
    count = bool(re.search(r"\b(?:how many|count|counts|breakdown|categor(?:y|ies)|status|statuses)\b", text))
    return (etr_subject and (timing or count)) or (timing and count and "incident" in text)


def _instant(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    if result.tzinfo is None or result.utcoffset() is None:
        return None
    return result.astimezone(timezone.utc)


def _eastern(value: datetime) -> str:
    return value.astimezone(EASTERN).strftime("%m/%d/%Y %H:%M %Z")


def _timeline_state(
    selected: ScenarioDescriptor,
    scenarios: list[ScenarioDescriptor],
    now: datetime,
) -> tuple[Literal["eligible", "future", "stale", "legacy", "unavailable"], str | None]:
    temporal = selected.temporal
    if temporal is None:
        return "legacy", None
    cutoff = temporal.as_of_at.astimezone(timezone.utc)
    if temporal.kind == "single_snapshot":
        return ("future" if cutoff > now else "eligible"), None
    siblings = [
        item for item in scenarios
        if item.temporal is not None
        and item.temporal.kind == "timeline_snapshot"
        and item.temporal.timeline_id == temporal.timeline_id
    ]
    if len(siblings) != temporal.snapshot_count:
        return "unavailable", None
    siblings.sort(key=lambda item: item.temporal.snapshot_index or 0)
    policy = temporal.model_dump(exclude={"as_of_at", "snapshot_index"})
    previous: datetime | None = None
    for index, sibling in enumerate(siblings, start=1):
        item = sibling.temporal
        if item is None or item.snapshot_index != index or item.snapshot_count != len(siblings):
            return "unavailable", None
        sibling_cutoff = item.as_of_at.astimezone(timezone.utc)
        if previous is not None and sibling_cutoff <= previous:
            return "unavailable", None
        if item.model_dump(exclude={"as_of_at", "snapshot_index"}) != policy:
            return "unavailable", None
        previous = sibling_cutoff
    listed = next((item for item in siblings if item.scenario_id == selected.scenario_id), None)
    if listed is None or listed.temporal != temporal:
        return "unavailable", None
    eligible = [item for item in siblings if item.temporal.as_of_at.astimezone(timezone.utc) <= now]
    latest = eligible[-1] if eligible else None
    if cutoff > now:
        return "future", latest.scenario_id if latest else None
    if latest is not None and latest.scenario_id != selected.scenario_id:
        return "stale", latest.scenario_id
    return "eligible", None


def analyze_etrs(
    incidents: list[Incident],
    selected: ScenarioDescriptor,
    scenarios: list[ScenarioDescriptor],
    received_at: datetime,
    mode: ETRMode,
) -> ETRAnalysis:
    now = received_at.astimezone(timezone.utc)
    temporal_status, suggested = _timeline_state(selected, scenarios, now)
    cutoff = selected.temporal.as_of_at if selected.temporal else None
    evaluation = cutoff if mode == "scenario_preview" and cutoff else now
    result = ETRAnalysis(
        mode=mode,
        status="blocked",
        temporal_status=temporal_status,
        evaluation_at=evaluation,
        scenario_as_of_at=cutoff,
        suggested_scenario_id=suggested,
    )
    if temporal_status in {"legacy", "unavailable"} or (
        mode == "current" and temporal_status != "eligible"
    ):
        return result

    evaluation_minute = evaluation.astimezone(timezone.utc).replace(second=0, microsecond=0)
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    examples: list[ETRExample] = []
    example_counts: Counter[str] = Counter()
    past_due = 0
    past_due_within_due_now = 0
    for incident in incidents:
        etr = _instant(incident.etr)
        reason = None
        if incident.etr_status == "assessing_conditions":
            category = "unavailable"
            reason = "assessing_conditions"
        elif etr is None:
            category = "unavailable"
            reason = "missing_or_invalid"
        else:
            etr_minute = etr.replace(second=0, microsecond=0)
            minutes = int((etr_minute - evaluation_minute).total_seconds() // 60)
            if minutes < 0:
                past_due += 1
            if minutes < -GRACE_MINUTES:
                category = "expired"
            elif minutes <= 0:
                category = "due_now"
                if minutes < 0:
                    past_due_within_due_now += 1
            elif minutes <= SOON_MINUTES:
                category = "due_soon"
            else:
                category = "valid_future"
        counts[category] += 1
        if reason:
            reasons[reason] += 1
        example_key = f"unavailable:{reason}" if reason else category
        example_limit = 1 if reason else 2
        if example_counts[example_key] < example_limit:
            examples.append(ETRExample(
                incident_id=incident.incident_id,
                category=category,
                etr=incident.etr if reason is None else None,
                unavailable_reason=reason,
            ))
            example_counts[example_key] += 1
    return result.model_copy(update={
        "status": "answered",
        "evaluated_incident_count": len(incidents),
        "counts": ETRCategoryCounts(**{name: counts[name] for name in CATEGORIES}),
        "unavailable_assessing_conditions": reasons["assessing_conditions"],
        "unavailable_missing_or_invalid": reasons["missing_or_invalid"],
        "past_due_total": past_due,
        "past_due_within_due_now": past_due_within_due_now,
        "examples": examples,
    })


def etr_answer(analysis: ETRAnalysis) -> str:
    cutoff = _eastern(analysis.scenario_as_of_at) if analysis.scenario_as_of_at else "unavailable"
    if analysis.status == "blocked":
        if analysis.temporal_status == "future":
            guidance = "The selected scenario is ahead of current time. Select an eligible earlier snapshot or choose Scenario preview to evaluate at its simulated cutoff."
        elif analysis.temporal_status == "stale":
            guidance = "A later timeline snapshot is already eligible. Select the latest eligible snapshot for a current-time answer, or choose Scenario preview for this historical state."
        elif analysis.temporal_status == "legacy":
            guidance = "This legacy scenario has no authoritative data-as-of cutoff, so its current-time ETR completeness cannot be verified."
        else:
            guidance = "Timeline sibling metadata could not be verified, so the current-time ETR assessment is unavailable."
        if analysis.suggested_scenario_id:
            guidance += f" Latest eligible scenario: {analysis.suggested_scenario_id}."
        return f"### ETR assessment unavailable\n\n{guidance}\n\nSelected scenario data as of: {cutoff}."
    counts = analysis.counts
    assert counts is not None
    mode_label = "Scenario preview" if analysis.mode == "scenario_preview" else "Current-time assessment"
    qualifier = (
        "This uses the selected snapshot's simulated cutoff, not the current clock."
        if analysis.mode == "scenario_preview"
        else "The incident inventory and ETR values are frozen at the selected scenario cutoff."
    )
    examples = ", ".join(f"{item.incident_id} ({item.category.replace('_', ' ')})" for item in analysis.examples)
    return (
        f"### ETR {mode_label.lower()}\n\n"
        f"{mode_label} at **{_eastern(analysis.evaluation_at)}**; incident data as of **{cutoff}**. {qualifier}\n\n"
        f"| ETR state | Incidents |\n| --- | ---: |\n"
        f"| Expired (more than 10 minutes past) | {counts.expired} |\n"
        f"| Due Now (10 minutes past through current minute) | {counts.due_now} |\n"
        f"| Due Soon (next 60 minutes) | {counts.due_soon} |\n"
        f"| Valid Future (more than 60 minutes ahead) | {counts.valid_future} |\n"
        f"| Unavailable | {counts.unavailable} |\n\n"
        f"**Total:** {analysis.evaluated_incident_count} active incidents, including ranking-withheld records. "
        f"Unavailable: {analysis.unavailable_assessing_conditions} Assessing Conditions and "
        f"{analysis.unavailable_missing_or_invalid} missing or invalid. "
        f"**Past-due ETRs:** {analysis.past_due_total}, including "
        f"{analysis.past_due_within_due_now} in the Due Now grace window."
        + (f"\n\nExamples: {examples}." if examples else "")
    )
