"""FastAPI route handlers."""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from config.settings import Settings
from providers.common import get_user_facing_error_message
from providers.exceptions import InvalidRequestError, ProviderError

from .dependencies import get_provider_for_type, get_settings, require_api_key
from .identity import cleanup_model_identity
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.responses import TokenCountResponse
from .optimization_handlers import try_optimizations
from .request_utils import get_token_count

router = APIRouter()


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    raw_request: Request,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """Create a message (always streaming)."""

    try:
        if not request_data.messages:
            raise InvalidRequestError("messages cannot be empty")

        # Support model override via API key (e.g. sk-ant-dummy:llama-4)
        header = (
            raw_request.headers.get("x-api-key")
            or raw_request.headers.get("authorization")
            or raw_request.headers.get("anthropic-auth-token")
        )
        if header and ":" in header:
            # Extract token and target model name from header
            # Handling both Bearer and raw formats
            token_part = (
                header.split(" ", 1)[1] if header.lower().startswith("bearer ") else header
            )
            if ":" in token_part:
                target_model_name = token_part.split(":", 1)[1]
                logger.debug(f"MODEL_HEADER_OVERRIDE: '{target_model_name}'")

                # Re-resolve and force update the request data
                resolved_full = settings.resolve_model(target_model_name)
                request_data.resolved_provider_model = resolved_full
                request_data.map_model()


        optimized = try_optimizations(request_data, settings)
        if optimized is not None:
            return optimized
        logger.debug("No optimization matched, routing to provider")

        # Cleanup model identity if enabled
        cleanup_model_identity(request_data, settings)

        # Resolve provider from the model-aware mapping
        provider_type = Settings.parse_provider_type(
            request_data.resolved_provider_model or settings.model
        )
        provider = get_provider_for_type(provider_type)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        logger.info(
            "API_REQUEST: request_id={} model={} messages={}",
            request_id,
            request_data.model,
            len(request_data.messages),
        )
        logger.debug("FULL_PAYLOAD [{}]: {}", request_id, request_data.model_dump())

        input_tokens = get_token_count(
            request_data.messages, request_data.system, request_data.tools
        )
        return StreamingResponse(
            provider.stream_response(
                request_data,
                input_tokens=input_tokens,
                request_id=request_id,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except ProviderError:
        raise
    except Exception as e:
        logger.error(f"Error: {e!s}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 500),
            detail=get_user_facing_error_message(e),
        ) from e


@router.post("/v1/messages/count_tokens")
async def count_tokens(request_data: TokenCountRequest, _auth=Depends(require_api_key)):
    """Count tokens for a request."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    with logger.contextualize(request_id=request_id):
        try:
            tokens = get_token_count(
                request_data.messages, request_data.system, request_data.tools
            )
            logger.info(
                "COUNT_TOKENS: request_id={} model={} messages={} input_tokens={}",
                request_id,
                getattr(request_data, "model", "unknown"),
                len(request_data.messages),
                tokens,
            )
            return TokenCountResponse(input_tokens=tokens)
        except Exception as e:
            logger.error(
                "COUNT_TOKENS_ERROR: request_id={} error={}\n{}",
                request_id,
                get_user_facing_error_message(e),
                traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500, detail=get_user_facing_error_message(e)
            ) from e


@router.get("/")
async def root(
    settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)
):
    """Root endpoint."""
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "model": settings.model,
    }


@router.get("/v1/users/me")
async def get_user_me(_auth=Depends(require_api_key)):
    """Mock identity endpoint for Claude CLI."""
    return {
        "id": "user_01ABC123",
        "email": "user@example.com",
        "first_name": "Claude",
        "last_name": "User",
        "created_at": "2024-01-01T00:00:00Z"
    }


@router.get("/v1/organizations")
async def get_organizations(_auth=Depends(require_api_key)):
    """Mock organizations endpoint for Claude CLI."""
    return {
        "data": [
            {
                "id": "org_01ABC123",
                "name": "Default Organization",
                "created_at": "2024-01-01T00:00:00Z",
                "role": "admin"
            }
        ],
        "has_more": False,
        "first_id": "org_01ABC123",
        "last_id": "org_01ABC123"
    }


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.post("/stop")
async def stop_cli(request: Request, _auth=Depends(require_api_key)):
    """Stop all CLI sessions and pending tasks."""
    handler = getattr(request.app.state, "message_handler", None)
    if not handler:
        # Fallback if messaging not initialized
        cli_manager = getattr(request.app.state, "cli_manager", None)
        if cli_manager:
            await cli_manager.stop_all()
            logger.info("STOP_CLI: source=cli_manager cancelled_count=N/A")
            return {"status": "stopped", "source": "cli_manager"}
        raise HTTPException(status_code=503, detail="Messaging system not initialized")

    count = await handler.stop_all_tasks()
    logger.info("STOP_CLI: source=handler cancelled_count={}", count)
    return {"status": "stopped", "cancelled_count": count}
