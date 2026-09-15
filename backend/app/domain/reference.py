from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator

from .models import DomainModel


ReferenceStatus = Literal["current", "stale", "unavailable", "invalid"]
ReferenceMatchStatus = Literal["found", "ambiguous", "not_found", "not_evaluated"]


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("must include a timezone offset")
    return value


class PsegReferenceRow(DomainModel):
    reference_id: str = Field(pattern=r"^pseg-li-[0-9a-f]{20}$")
    source_county: str = Field(min_length=1)
    source_township: str = Field(min_length=1)
    source_village: str = Field(min_length=1)
    county: str = Field(min_length=1)
    township: str = Field(min_length=1)
    village: str = Field(min_length=1)
    customers_served: int = Field(ge=0)

    @field_validator(
        "reference_id",
        "source_county",
        "source_township",
        "source_village",
        "county",
        "township",
        "village",
    )
    @classmethod
    def normalize_non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("customers_served", mode="before")
    @classmethod
    def require_integer_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.isdigit():
            raise ValueError("must be a non-negative integer")
        return value


class PsegReferenceSource(DomainModel):
    organization: Literal["PSEG Long Island"]
    product: Literal["KUBRA Storm Center"]
    current_state_url: str = Field(min_length=1)
    report_url: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    view_id: str = Field(min_length=1)
    report_id: str = Field(min_length=1)
    interval_id: str = Field(min_length=1)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class PsegReferenceExtractor(DomainModel):
    repository: str = Field(min_length=1)
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    working_tree_dirty: Literal[False]


class PsegReferenceArtifact(DomainModel):
    file_name: Literal["customers-served.csv"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PsegReferenceCounts(DomainModel):
    county: int = Field(ge=1)
    township: int = Field(ge=1)
    leaf: int = Field(ge=1)


class PsegReferenceReconciliation(DomainModel):
    status: Literal["passed"]


class PsegReferenceReview(DomainModel):
    status: Literal["approved"]
    reviewed_by_role: str = Field(min_length=1)
    reviewed_at: datetime

    @field_validator("reviewed_by_role")
    @classmethod
    def normalize_reviewer_role(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class PsegReferenceManifest(DomainModel):
    dataset_id: Literal["pseg-li-customers-served"]
    schema_version: Literal["1.0"]
    source: PsegReferenceSource
    extracted_at: datetime
    extractor: PsegReferenceExtractor
    artifact: PsegReferenceArtifact
    counts: PsegReferenceCounts
    total_customers_served: int = Field(ge=0)
    reconciliation: PsegReferenceReconciliation
    normalization_rule_version: Literal["poc-012-v1"]
    review: PsegReferenceReview
    supersedes: Optional[str] = None

    @field_validator("extracted_at")
    @classmethod
    def validate_extracted_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "PsegReferenceManifest":
        if self.extracted_at < self.source.updated_at:
            raise ValueError("extracted_at must not precede source.updated_at")
        if self.review.reviewed_at < self.extracted_at:
            raise ValueError("review.reviewed_at must not precede extracted_at")
        return self


class ReferenceValidationIssue(DomainModel):
    location: str
    message: str
    type: Optional[str] = None


class ReferenceValidationResult(DomainModel):
    reference_status: ReferenceStatus
    issues: list[ReferenceValidationIssue] = Field(default_factory=list)
    source_updated_at: Optional[datetime] = None
    extracted_at: Optional[datetime] = None
    age_days: Optional[float] = None
    stale_after_days: int = 90


class PsegReferenceProvenance(DomainModel):
    dataset_id: str
    schema_version: str
    source_organization: str
    source_product: str
    report_url: str
    source_updated_at: datetime
    extracted_at: datetime
    extractor_repository: str
    extractor_commit: str
    normalization_rule_version: str
    reviewed_by_role: str
    reviewed_at: datetime


class PsegReferenceSnapshot(DomainModel):
    validation: ReferenceValidationResult
    rows: list[PsegReferenceRow] = Field(default_factory=list)
    provenance: Optional[PsegReferenceProvenance] = None


class ReferenceLookupQuery(DomainModel):
    kind: Literal["county", "township", "village", "path", "alias"]
    county: Optional[str] = None
    township: Optional[str] = None
    village: Optional[str] = None
    alias: Optional[str] = None


class PsegReferenceLookupResult(DomainModel):
    reference_status: ReferenceStatus
    match_status: ReferenceMatchStatus
    query: ReferenceLookupQuery
    matches: list[PsegReferenceRow] = Field(default_factory=list)
    total_customers_served: Optional[int] = None
    provenance: Optional[PsegReferenceProvenance] = None
    issues: list[ReferenceValidationIssue] = Field(default_factory=list)

