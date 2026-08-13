from __future__ import annotations

import logging
import re
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from .scenario_service import ScenarioServiceError
from .services.errors import DecisionConflictError, DecisionReasonRequiredError, EntityNotFoundError


logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ErrorDetail(BaseModel):
    """Machine-readable, client-safe context for one error."""

    model_config = ConfigDict(extra="allow")

    message: str
    location: Optional[str] = None
    type: Optional[str] = None


class ApiError(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[ErrorDetail] = Field(default_factory=list)
    entity: Optional[str] = None
    entity_id: Optional[str] = None
    scenario_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ApiError


_CORRELATION_ID_RESPONSE_HEADER = {
    CORRELATION_ID_HEADER: {
        "description": "Identifier for correlating this response with backend diagnostics.",
        "schema": {"type": "string"},
    }
}

ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Invalid domain operation",
        "headers": _CORRELATION_ID_RESPONSE_HEADER,
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "headers": _CORRELATION_ID_RESPONSE_HEADER,
    },
    409: {
        "model": ErrorResponse,
        "description": "Domain state conflict",
        "headers": _CORRELATION_ID_RESPONSE_HEADER,
    },
    422: {
        "model": ErrorResponse,
        "description": "Request or scenario validation failed",
        "headers": _CORRELATION_ID_RESPONSE_HEADER,
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error",
        "headers": _CORRELATION_ID_RESPONSE_HEADER,
    },
}


def _correlation_id(request: Request) -> str:
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        return correlation_id

    correlation_id = str(uuid4())
    request.state.correlation_id = correlation_id
    return correlation_id


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
    scenario_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    correlation_id = _correlation_id(request)
    response_headers = dict(headers or {})
    response_headers[CORRELATION_ID_HEADER] = correlation_id
    payload = ErrorResponse(
        error=ApiError(
            code=code,
            message=message,
            correlation_id=correlation_id,
            details=[ErrorDetail.model_validate(detail) for detail in details or []],
            entity=entity,
            entity_id=entity_id,
            scenario_id=scenario_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers=response_headers,
    )


async def _entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    return _error_response(
        request,
        status_code=404,
        code="entity_not_found",
        message=str(exc),
        entity=exc.entity,
        entity_id=exc.entity_id,
    )


async def _decision_reason_required_handler(
    request: Request,
    exc: DecisionReasonRequiredError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=400,
        code="decision_reason_required",
        message=str(exc),
        details=[
            {
                "location": "body.reason",
                "message": f"A reason is required when a recommendation is {exc.action}.",
                "type": "value_error.missing_reason",
                "action": exc.action,
            }
        ],
    )


async def _decision_conflict_handler(request: Request, exc: DecisionConflictError) -> JSONResponse:
    return _error_response(
        request,
        status_code=409,
        code="decision_incident_mismatch",
        message=str(exc),
        details=[
            {
                "location": "body.recommendation.incident_id",
                "message": "The recommendation must belong to the decision incident.",
                "type": "value_error.decision_conflict",
                "expected": exc.incident_id,
                "actual": exc.recommendation_incident_id,
            }
        ],
        entity="Incident",
        entity_id=exc.incident_id,
    )


async def _scenario_service_error_handler(
    request: Request,
    exc: ScenarioServiceError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        scenario_id=exc.scenario_id,
    )


async def _request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "location": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="request_validation_failed",
        message="Request validation failed.",
        details=details,
    )


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "resource_not_found",
        405: "method_not_allowed",
        409: "conflict",
        503: "service_unavailable",
    }
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return _error_response(
        request,
        status_code=exc.status_code,
        code=codes.get(exc.status_code, "http_error"),
        message=message,
        headers=exc.headers,
    )


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = _correlation_id(request)
    logger.exception("Unhandled API error; correlation_id=%s", correlation_id)
    return _error_response(
        request,
        status_code=500,
        code="internal_server_error",
        message="An unexpected server error occurred.",
    )


def install_error_contract(app: FastAPI) -> None:
    """Install correlation propagation and the shared public error boundary."""

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        requested_id = request.headers.get(CORRELATION_ID_HEADER, "")
        request.state.correlation_id = (
            requested_id if _CORRELATION_ID_PATTERN.fullmatch(requested_id) else str(uuid4())
        )
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = request.state.correlation_id
        return response

    app.add_exception_handler(EntityNotFoundError, _entity_not_found_handler)
    app.add_exception_handler(DecisionReasonRequiredError, _decision_reason_required_handler)
    app.add_exception_handler(DecisionConflictError, _decision_conflict_handler)
    app.add_exception_handler(ScenarioServiceError, _scenario_service_error_handler)
    app.add_exception_handler(RequestValidationError, _request_validation_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)
