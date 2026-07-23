"""FastAPI app factory and entrypoint."""

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
import time
import uuid
import logging
from pydantic import ValidationError as PydanticValidationError

from hospital_command_center.api.deps import verify_api_key
from hospital_command_center.api.routes import encounters, followup, health, intake, triage, webhooks, workflow
from hospital_command_center.core.config import WELCOME_MESSAGE, get_settings
from hospital_command_center.core.exceptions import (
    IntakeError,
    NotConfiguredError,
    RoutingError,
    TriageError,
    WorkflowError,
)
from hospital_command_center.core.logging import configure_logging

configure_logging()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    request_logger = logging.getLogger("hospital_command_center.requests")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        request_logger.info(
            "request_started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "has_api_key": "x-api-key" in request.headers,
            },
        )

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        request_logger.info(
            "request_finished",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(NotConfiguredError)
    async def not_configured_handler(_request: Request, exc: NotConfiguredError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(IntakeError)
    async def intake_error_handler(_request: Request, exc: IntakeError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(TriageError)
    async def triage_error_handler(_request: Request, exc: TriageError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(RoutingError)
    async def routing_error_handler(_request: Request, exc: RoutingError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(_request: Request, exc: WorkflowError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    
    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(_request: Request, exc: PydanticValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": WELCOME_MESSAGE}

    prefix = settings.api_prefix
    protected = {"dependencies": [Depends(verify_api_key)]}

    app.include_router(health.router, prefix=prefix)  # no auth — health check must always be reachable
    app.include_router(intake.router, prefix=prefix, **protected)
    app.include_router(triage.router, prefix=prefix, **protected)
    app.include_router(workflow.router, prefix=prefix, **protected)
    app.include_router(encounters.router, prefix=prefix, **protected)
    app.include_router(followup.router, prefix=prefix, **protected)
    app.include_router(webhooks.router, prefix=prefix, **protected)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "hospital_command_center.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()