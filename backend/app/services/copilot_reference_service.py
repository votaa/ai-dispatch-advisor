from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from ..api_models import CopilotEvidence
from ..domain.models import Incident
from ..domain.reference import PsegReferenceLookupResult, PsegReferenceRow
from ..geography import GeographyRegistry
from ..scenario_service import ScenarioDescriptor
from .incident_service import IncidentService
from .reference_service import PsegLongIslandReferenceService


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _contains_phrase(message: str, phrase: str) -> bool:
    return f" {_normalized_text(phrase)} " in f" {_normalized_text(message)} "


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CopilotReferenceAnswer:
    answer: str
    intent: str
    evidence: list[CopilotEvidence]
    source: str
    response_scope: str
    warning: str | None = None
    data_snapshot_at: str | None = None


class CopilotReferenceService:
    """Deterministic Copilot answers over approved POC-012 reference data."""

    def __init__(
        self,
        *,
        reference: PsegLongIslandReferenceService,
        geography: GeographyRegistry,
        incidents: IncidentService,
        active_scenario: Callable[[], ScenarioDescriptor],
    ) -> None:
        self._reference = reference
        self._geography = geography
        self._incidents = incidents
        self._active_scenario = active_scenario

    @staticmethod
    def is_query(normalized: str) -> bool:
        if "all customers served" in normalized and not any(
            term in normalized
            for term in ("county", "township", "town of", "village", "hierarchy")
        ):
            return False
        if any(
            term in normalized
            for term in ("customers served", "customers are served", "customer served")
        ):
            return True
        if any(term in normalized for term in ("percentage", "percent")) and any(
            term in normalized
            for term in ("customers", "outage", "out", "without power")
        ):
            return True
        if "hierarchy" in normalized:
            return True
        return (
            "match" in normalized
            and "township" in normalized
            and "village" in normalized
        )

    def answer(
        self,
        message: str,
        selected_incident: Incident | None,
        *,
        use_selected_incident: bool,
    ) -> CopilotReferenceAnswer:
        lookup = self._resolve_lookup(
            message,
            selected_incident if use_selected_incident else None,
        )
        if lookup is None:
            return CopilotReferenceAnswer(
                answer=(
                    "## PSEG Long Island reference\n\n"
                    "Specify a County, Township, Village, configured alias, or selected "
                    "incident. No geographic scope was inferred from model knowledge."
                ),
                intent="reference_area_unresolved",
                evidence=[],
                source="approved-static-reference",
                warning="Reference query requires an explicit resolvable geographic scope.",
                response_scope="No PSEG Long Island reference area evaluated",
            )
        normalized = _normalized_text(message)
        if any(term in normalized for term in ("percentage", "percent")):
            return self._outage_percentage(lookup)
        if "hierarchy" in normalized or (
            "match" in normalized
            and "township" in normalized
            and "village" in normalized
        ):
            return self._hierarchy_answer(lookup)
        return self._customers_served_answer(lookup)

    def _resolve_lookup(
        self,
        message: str,
        selected_incident: Incident | None,
    ) -> PsegReferenceLookupResult | None:
        normalized = _normalized_text(message)
        snapshot = self._reference.snapshot()
        rows = snapshot.rows

        counties = {row.county for row in rows}
        townships = {row.township for row in rows}
        villages = {row.village for row in rows}
        if not rows:
            counties.update(record.county for record in self._geography.records)
            townships.update(record.township for record in self._geography.records)
            villages.update(record.village for record in self._geography.records)

        if "county" in normalized:
            name = self._first_mentioned(message, counties)
            if name is not None:
                return self._reference.by_county(name)
        if "town" in normalized or "township" in normalized:
            name = self._first_mentioned(message, townships)
            if name is not None:
                county = self._first_mentioned(message, counties)
                return self._reference.by_township(name, county=county)
        if "village" in normalized:
            name = self._first_mentioned(message, villages)
            if name is not None:
                return self._reference.by_village(name)

        source_villages = {
            row.source_village: row.village
            for row in rows
            if _normalized_text(row.source_village) != _normalized_text(row.village)
        }
        source_name = self._first_mentioned(message, source_villages)
        if source_name is not None:
            return self._reference.by_village(source_villages[source_name])

        name = self._first_mentioned(message, villages)
        if name is not None:
            return self._reference.by_village(name)
        alias = self._first_mentioned(message, self._reference.aliases)
        if alias is not None:
            return self._reference.by_alias(alias)
        name = self._first_mentioned(message, townships)
        if name is not None:
            return self._reference.by_township(name)
        name = self._first_mentioned(message, counties)
        if name is not None:
            return self._reference.by_county(name)

        if selected_incident is not None:
            location = self._geography.hierarchy_for_incident(selected_incident)
            if location is not None:
                return self._reference.by_path(
                    location.county,
                    location.township,
                    location.village,
                )
        return None

    @staticmethod
    def _first_mentioned(
        message: str,
        values: Iterable[str],
    ) -> str | None:
        return next(
            (
                value
                for value in sorted(set(values), key=lambda item: (-len(item), item))
                if _contains_phrase(message, value)
            ),
            None,
        )

    def _customers_served_answer(
        self,
        lookup: PsegReferenceLookupResult,
    ) -> CopilotReferenceAnswer:
        unavailable = self._unavailable_answer(lookup, "reference_customers_served")
        if unavailable is not None:
            return unavailable
        if lookup.match_status == "not_found":
            return self._not_found_answer(lookup, "reference_customers_served")
        if lookup.match_status == "ambiguous":
            return self._ambiguous_answer(lookup, "reference_customers_served")

        normalized_scope, source_scope = self._scope_labels(lookup)
        provenance = lookup.provenance
        assert provenance is not None
        total = lookup.total_customers_served
        assert total is not None
        answer = (
            "## PSEG Long Island customers served\n\n"
            f"**{total:,} customers served** in the approved static reference.\n\n"
            f"- **Normalized scope:** {normalized_scope}\n"
            f"- **KUBRA source scope:** {source_scope}\n"
            f"- **Reference source timestamp:** {_utc_text(provenance.source_updated_at)}\n"
            f"- **Extracted:** {_utc_text(provenance.extracted_at)}\n"
            f"- **Freshness:** {lookup.reference_status.title()}\n\n"
            "This is an SME-approved static customers-served value, not a live outage count."
        )
        return CopilotReferenceAnswer(
            answer=answer,
            intent="reference_customers_served",
            evidence=self._reference_evidence(lookup),
            source="approved-static-reference",
            warning=self._freshness_warning(lookup),
            response_scope=(
                f"Approved static reference: {len(lookup.matches)} leaf record(s) "
                f"aggregated for {normalized_scope}"
            ),
            data_snapshot_at=_utc_text(provenance.source_updated_at),
        )

    def _hierarchy_answer(
        self,
        lookup: PsegReferenceLookupResult,
    ) -> CopilotReferenceAnswer:
        unavailable = self._unavailable_answer(lookup, "reference_hierarchy")
        if unavailable is not None:
            return unavailable
        if lookup.match_status == "not_found":
            return self._not_found_answer(lookup, "reference_hierarchy")
        if lookup.match_status == "ambiguous":
            return self._ambiguous_answer(lookup, "reference_hierarchy")

        normalized_scope, source_scope = self._scope_labels(lookup)
        provenance = lookup.provenance
        assert provenance is not None
        shown = lookup.matches[:10]
        table = "\n".join(
            f"| {row.source_county} → {row.source_township} → {row.source_village} | "
            f"{row.county} → {row.township} → {row.village} | "
            f"{row.customers_served:,} |"
            for row in shown
        )
        answer = (
            "## PSEG Long Island reference hierarchy\n\n"
            f"- **Normalized scope:** {normalized_scope}\n"
            f"- **KUBRA source scope:** {source_scope}\n"
            f"- **Customers served:** {lookup.total_customers_served:,}\n"
            f"- **Reference source timestamp:** {_utc_text(provenance.source_updated_at)}\n"
            f"- **Extracted:** {_utc_text(provenance.extracted_at)}\n"
            f"- **Freshness:** {lookup.reference_status.title()}\n\n"
            "### Matching source and normalized leaf paths "
            f"(showing {len(shown)} of {len(lookup.matches)})\n\n"
            "| KUBRA source path | AIDA normalized path | Customers served |\n"
            "| --- | --- | ---: |\n"
            f"{table}"
        )
        return CopilotReferenceAnswer(
            answer=answer,
            intent="reference_hierarchy",
            evidence=self._reference_evidence(lookup),
            source="approved-static-reference",
            warning=self._freshness_warning(lookup),
            response_scope=(
                f"Approved static hierarchy: {len(lookup.matches)} leaf record(s) "
                f"match {normalized_scope}"
            ),
            data_snapshot_at=_utc_text(provenance.source_updated_at),
        )

    def _outage_percentage(
        self,
        lookup: PsegReferenceLookupResult,
    ) -> CopilotReferenceAnswer:
        unavailable = self._unavailable_answer(lookup, "reference_outage_percentage")
        if unavailable is not None:
            return unavailable
        if lookup.match_status == "not_found":
            return self._not_found_answer(lookup, "reference_outage_percentage")
        if lookup.match_status == "ambiguous":
            return self._ambiguous_answer(lookup, "reference_outage_percentage")

        normalized_scope, source_scope = self._scope_labels(lookup)
        denominator = lookup.total_customers_served
        assert denominator is not None
        provenance = lookup.provenance
        assert provenance is not None
        if lookup.reference_status == "stale":
            return self._percentage_refusal(
                lookup,
                normalized_scope,
                (
                    f"The static denominator is {denominator:,} customers served, but its "
                    "source timestamp is older than the approved 90-day limit."
                ),
                "Mixed-source percentage blocked because the reference denominator is stale.",
            )
        if denominator == 0:
            return self._percentage_refusal(
                lookup,
                normalized_scope,
                "The approved static customers-served denominator is zero.",
                "Mixed-source percentage blocked because division by zero is not allowed.",
            )

        descriptor = self._active_scenario()
        if descriptor.freshness is None:
            return self._percentage_refusal(
                lookup,
                normalized_scope,
                "The active synthetic scenario has no approved snapshot timestamp.",
                "Mixed-source percentage blocked because numerator freshness is unavailable.",
            )

        reference_rows = self._reference.snapshot().rows
        reference_paths = {
            (row.county, row.township, row.village) for row in reference_rows
        }
        reference_paths_by_id = {
            row.reference_id: (row.county, row.township, row.village)
            for row in reference_rows
        }
        target_paths = {
            (row.county, row.township, row.village) for row in lookup.matches
        }
        incidents = self._incidents.list_visible()
        located: list[tuple[Incident, tuple[str, str, str]]] = []
        unresolved: list[Incident] = []
        for incident in incidents:
            if incident.geography_reference_id:
                path = reference_paths_by_id.get(incident.geography_reference_id)
                if path is None:
                    unresolved.append(incident)
                    continue
                located.append((incident, path))
                continue
            location = self._geography.hierarchy_for_incident(incident)
            if location is None:
                unresolved.append(incident)
                continue
            path = (location.county, location.township, location.village)
            if path not in reference_paths:
                unresolved.append(incident)
                continue
            located.append((incident, path))
        if unresolved:
            return self._percentage_refusal(
                lookup,
                normalized_scope,
                (
                    f"{len(unresolved)} active synthetic incident record(s) cannot be aligned "
                    "to the approved reference hierarchy, so the area numerator is incomplete."
                ),
                "Mixed-source percentage blocked because geographic coverage is partial.",
            )

        numerator_records = [
            incident for incident, path in located if path in target_paths
        ]
        numerator = sum(incident.customers_out for incident in numerator_records)
        percentage = numerator / denominator * 100
        scenario_timestamp = _utc_text(descriptor.freshness.updated_at)
        reference_timestamp = _utc_text(provenance.source_updated_at)
        evidence = [
            self._reference_evidence(lookup)[0],
            CopilotEvidence(
                source_type="dashboard",
                record_id=descriptor.scenario_id,
                label=(
                    f"Complete synthetic numerator: {len(numerator_records)} active "
                    f"incident record(s), {numerator:,} customers out"
                ),
            ),
            *[
                CopilotEvidence(
                    source_type="incident",
                    record_id=incident.incident_id,
                    label=(
                        f"Synthetic numerator record: {incident.municipality}, "
                        f"{incident.customers_out:,} customers out"
                    ),
                )
                for incident in numerator_records[:10]
            ],
        ]
        answer = (
            "## Mixed-source outage percentage\n\n"
            f"**{numerator:,} synthetic customers out ÷ {denominator:,} static customers "
            f"served = {percentage:.2f}%** for {normalized_scope}.\n\n"
            f"- **Numerator:** Complete active-scenario aggregate from "
            f"`{descriptor.scenario_id}`; {len(numerator_records)} incident record(s); "
            f"snapshot {scenario_timestamp}; provenance: {descriptor.freshness.provenance}.\n"
            f"- **Denominator:** SME-approved static PSEG Long Island reference; "
            f"KUBRA scope {source_scope}; source timestamp {reference_timestamp}; "
            f"extracted {_utc_text(provenance.extracted_at)}; freshness Current.\n\n"
            "This deliberately mixes synthetic outage data with a static reference denominator. "
            "It is not a live PSEG Long Island outage percentage."
        )
        return CopilotReferenceAnswer(
            answer=answer,
            intent="reference_outage_percentage",
            evidence=evidence,
            source="synthetic-demo-data + approved-static-reference",
            response_scope=(
                f"Complete aligned area calculation for {normalized_scope}: "
                f"{len(incidents)} active incidents evaluated"
            ),
            data_snapshot_at=scenario_timestamp,
        )

    def _percentage_refusal(
        self,
        lookup: PsegReferenceLookupResult,
        normalized_scope: str,
        reason: str,
        warning: str,
    ) -> CopilotReferenceAnswer:
        provenance = lookup.provenance
        return CopilotReferenceAnswer(
            answer=(
                "## Mixed-source outage percentage unavailable\n\n"
                f"No percentage was calculated for {normalized_scope}. {reason}\n\n"
                "No numerator or denominator was inferred from model memory."
            ),
            intent="reference_outage_percentage",
            evidence=self._reference_evidence(lookup),
            source="synthetic-demo-data + approved-static-reference",
            warning=warning,
            response_scope=f"Refused mixed-source calculation for {normalized_scope}",
            data_snapshot_at=(
                _utc_text(provenance.source_updated_at) if provenance is not None else None
            ),
        )

    def _ambiguous_answer(
        self,
        lookup: PsegReferenceLookupResult,
        intent: str,
    ) -> CopilotReferenceAnswer:
        shown = lookup.matches[:10]
        table = "\n".join(
            f"| {row.county} → {row.township} → {row.village} | "
            f"{row.source_county} → {row.source_township} → {row.source_village} | "
            f"{row.customers_served:,} |"
            for row in shown
        )
        provenance = lookup.provenance
        return CopilotReferenceAnswer(
            answer=(
                "## Ambiguous PSEG Long Island area\n\n"
                f"{len(lookup.matches)} reference paths match that name. No Township was "
                "selected silently; specify a complete path.\n\n"
                "### Matching paths "
                f"(showing {len(shown)} of {len(lookup.matches)})\n\n"
                "| Normalized path | KUBRA source path | Customers served |\n"
                "| --- | --- | ---: |\n"
                f"{table}"
            ),
            intent=intent,
            evidence=self._reference_evidence(lookup),
            source="approved-static-reference",
            warning="Ambiguous area name; no customer counts were combined.",
            response_scope=f"Ambiguous static-reference lookup: {len(lookup.matches)} paths",
            data_snapshot_at=(
                _utc_text(provenance.source_updated_at) if provenance is not None else None
            ),
        )

    def _unavailable_answer(
        self,
        lookup: PsegReferenceLookupResult,
        intent: str,
    ) -> CopilotReferenceAnswer | None:
        if lookup.reference_status not in {"unavailable", "invalid"}:
            return None
        label = (
            "unavailable"
            if lookup.reference_status == "unavailable"
            else "invalid and was rejected"
        )
        return CopilotReferenceAnswer(
            answer=(
                "## PSEG Long Island reference unavailable\n\n"
                f"The approved static reference is {label}. No customers-served value, "
                "hierarchy, or percentage was inferred from model memory."
            ),
            intent=intent,
            evidence=[],
            source="approved-static-reference",
            warning=f"Reference status: {lookup.reference_status}.",
            response_scope="No approved PSEG Long Island reference records evaluated",
        )

    def _not_found_answer(
        self,
        lookup: PsegReferenceLookupResult,
        intent: str,
    ) -> CopilotReferenceAnswer:
        provenance = lookup.provenance
        return CopilotReferenceAnswer(
            answer=(
                "## PSEG Long Island reference\n\n"
                "No approved reference path matches the requested area. No value was "
                "inferred from model memory."
            ),
            intent=intent,
            evidence=[],
            source="approved-static-reference",
            warning="Requested area was not found in the approved static reference.",
            response_scope="Approved static-reference lookup returned no matching paths",
            data_snapshot_at=(
                _utc_text(provenance.source_updated_at) if provenance is not None else None
            ),
        )

    @staticmethod
    def _scope_labels(
        lookup: PsegReferenceLookupResult,
    ) -> tuple[str, str]:
        first = lookup.matches[0]
        if lookup.query.kind == "county":
            normalized = f"County {first.county}"
            source = first.source_county
        elif lookup.query.kind == "township":
            normalized = f"{first.county} → Township {first.township}"
            source = f"{first.source_county} → {first.source_township}"
        else:
            normalized = f"{first.county} → {first.township} → {first.village}"
            source = (
                f"{first.source_county} → {first.source_township} → "
                f"{first.source_village}"
            )
        return normalized, source

    @staticmethod
    def _freshness_warning(lookup: PsegReferenceLookupResult) -> str | None:
        if lookup.reference_status != "stale":
            return None
        return (
            "Static reference is older than 90 days. Customers-served values remain visible, "
            "but mixed-source percentage calculations are blocked."
        )

    @staticmethod
    def _reference_evidence(
        lookup: PsegReferenceLookupResult,
    ) -> list[CopilotEvidence]:
        if not lookup.matches:
            return []
        if lookup.match_status == "ambiguous":
            return [
                CopilotEvidence(
                    source_type="pseg_reference",
                    record_id=row.reference_id,
                    label=(
                        f"Approved static reference: {row.county} → {row.township} → "
                        f"{row.village}; {row.customers_served:,} customers served"
                    ),
                )
                for row in lookup.matches[:10]
            ]
        first: PsegReferenceRow = lookup.matches[0]
        if len(lookup.matches) == 1:
            record_id = first.reference_id
        else:
            query_parts = [
                lookup.query.county,
                lookup.query.township,
                lookup.query.village,
                lookup.query.alias,
            ]
            scope_id = ":".join(
                _normalized_text(part).replace(" ", "-")
                for part in query_parts
                if part
            )
            record_id = f"pseg-li-customers-served:{lookup.query.kind}:{scope_id}"
        return [
            CopilotEvidence(
                source_type="pseg_reference",
                record_id=record_id,
                label=(
                    f"Approved static reference aggregate: {len(lookup.matches)} leaf "
                    f"record(s), {lookup.total_customers_served:,} customers served"
                ),
            )
        ]
