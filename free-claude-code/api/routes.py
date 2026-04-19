"""FastAPI route handlers."""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
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

        # Explicitly resolve any Claude CLI model aliases to the configured provider ID.
        # This ensures aliases like 'claude-sonnet-4-6' are correctly mapped.
        resolved = settings.resolve_model(request_data.model)
        request_data.resolved_provider_model = resolved
        request_data.map_model()

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
                "anthropic-version": "2023-06-01",
                "x-anthropic-version": "2023-06-01",
            },
        )

    except ProviderError:
        raise
    except Exception as e:
        import datetime
        tb = traceback.format_exc()
        raw_error = str(e)
        
        # Store for diagnostics
        if hasattr(raw_request.app.state, "last_error"):
            raw_request.app.state.last_error = {
                "message": raw_error,
                "traceback": tb,
                "timestamp": datetime.datetime.now().isoformat(),
                "model_attempted": request_data.model,
                "provider_model": request_data.resolved_provider_model
            }
            
        logger.error(f"Error: {raw_error}\n{tb}")
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
    return JSONResponse(
        content={
            "status": "ok",
            "provider": settings.provider_type,
            "model": settings.model,
        },
        headers={
            "anthropic-version": "2023-06-01",
            "x-anthropic-version": "2023-06-01"
        }
    )


@router.get("/v1/users/me")
async def get_user_me(_auth=Depends(require_api_key)):
    """Full mock identity endpoint for Claude CLI v2 compatibility."""
    return JSONResponse(
        content={
            "id": "user_01ABC123",
            "email": "user@example.com",
            "first_name": "Claude",
            "last_name": "User",
            "created_at": "2024-01-01T00:00:00Z",
            "account": {
                "id": "acc_01ABC123",
                "name": "Personal Account",
                "settings": {
                    "default_organization_id": "org_01ABC123"
                }
            }
        },
        headers={
            "anthropic-version": "2023-06-01",
            "x-anthropic-version": "2023-06-01"
        }
    )


@router.get("/v1/organizations")
async def get_organizations(_auth=Depends(require_api_key)):
    """Full mock organizations endpoint with expanded capabilities for CLI v2."""
    return JSONResponse(
        content={
            "data": [
                {
                    "id": "org_01ABC123",
                    "name": "Default Organization",
                    "created_at": "2024-01-01T00:00:00Z",
                    "role": "admin",
                    "capabilities": [
                        "can_use_sonnet", 
                        "can_use_opus", 
                        "can_use_haiku",
                        "can_use_claude_sonnet_4_6",
                        "can_use_claude_sonnet_3_5",
                        "can_use_claude_haiku_4_5",
                        "can_use_claude_haiku_4_5_20251001",
                        "can_use_claude_opus_4_7",
                        "can_use_claude_opus_3",
                        "can_use_custom_models"
                    ]
                }
            ],
            "has_more": False,
            "first_id": "org_01ABC123",
            "last_id": "org_01ABC123"
        },
        headers={
            "anthropic-version": "2023-06-01",
            "x-anthropic-version": "2023-06-01"
        }
    )


@router.get("/v1/models")
async def get_models(_auth=Depends(require_api_key)):
    """Full mock models catalog for Claude CLI v2 compatibility."""
    return JSONResponse(
        content={
            "data": [
                {
                    "type": "model",
                    "id": "claude-3-5-sonnet-20241022",
                    "display_name": "Claude 3.5 Sonnet",
                    "created_at": "2024-10-22T00:00:00Z"
                },
                {
                    "type": "model",
                    "id": "claude-3-5-haiku-20241022",
                    "display_name": "Claude 3.5 Haiku",
                    "created_at": "2024-10-22T00:00:00Z"
                },
                {
                    "type": "model",
                    "id": "claude-3-5-opus-20240229",
                    "display_name": "Claude 3 Opus",
                    "created_at": "2024-02-29T00:00:00Z"
                },
                {
                    "type": "model",
                    "id": "claude-sonnet-4-6",
                    "display_name": "Claude Sonnet 4.6 (Next-Gen)",
                    "created_at": "2025-01-01T00:00:00Z"
                },
                {
                    "type": "model",
                    "id": "claude-haiku-4-5-20251001",
                    "display_name": "Claude Haiku 4.5 (Next-Gen)",
                    "created_at": "2025-10-01T00:00:00Z"
                }
            ],
            "has_more": False,
            "first_id": "claude-3-5-sonnet-20241022",
            "last_id": "claude-haiku-4-5-20251001"
        },
        headers={
            "anthropic-version": "2023-06-01",
            "x-anthropic-version": "2023-06-01"
        }
    )


@router.get("/v1/diagnostics")
async def get_diagnostics(raw_request: Request, settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)):
    """Masked diagnostics for troubleshooting Render environment."""
    last_err = getattr(raw_request.app.state, "last_error", None)
    return {
        "status": "ready",
        "has_nvidia_key": bool(settings.nvidia_nim_api_key),
        "nvidia_key_preview": f"{settings.nvidia_nim_api_key[:8]}..." if settings.nvidia_nim_api_key else "MISSING",
        "model": settings.model,
        "sonnet_model": settings.model_sonnet,
        "anthropic_version_supported": "2023-06-01",
        "last_error": last_err
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
