"""Pydantic models for Anthropic-compatible requests."""

from enum import StrEnum
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, field_validator, model_validator

from config.settings import Settings, get_settings


# =============================================================================
# Content Block Types
# =============================================================================
class Role(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: dict[str, Any]


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str | list[Any] | dict[str, Any]


class ContentBlockThinking(BaseModel):
    type: Literal["thinking"]
    thinking: str


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


# =============================================================================
# Message Types
# =============================================================================
class Message(BaseModel):
    model_config = {"extra": "allow"}
    role: Literal["user", "assistant", "system"]
    content: (
        str
        | list[
            ContentBlockText
            | ContentBlockImage
            | ContentBlockToolUse
            | ContentBlockToolResult
            | ContentBlockThinking
        ]
    )
    reasoning_content: str | None = None


def _extract_system_messages(
    messages: list[Message],
    system: str | list[SystemContent] | None
) -> tuple[list[Message], str | list[SystemContent] | None]:
    """Helper to extract system messages from the messages array and merge into system field."""
    system_msgs = [m for m in messages if m.role == "system"]
    if not system_msgs:
        return messages, system

    remaining_messages = [m for m in messages if m.role != "system"]

    extracted_texts = []
    for msg in system_msgs:
        if isinstance(msg.content, str):
            extracted_texts.append(msg.content)
        elif isinstance(msg.content, list):
            for block in msg.content:
                if hasattr(block, "text"):
                    extracted_texts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    extracted_texts.append(block["text"])

    if extracted_texts:
        additional_system = "\n\n".join(extracted_texts)
        if not system:
            system = additional_system
        elif isinstance(system, str):
            system = f"{system}\n\n{additional_system}"
        elif isinstance(system, list):
            for text in extracted_texts:
                system.append(SystemContent(type="text", text=text))

    return remaining_messages, system


class Tool(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any]


class ThinkingConfig(BaseModel):
    model_config = {"extra": "allow"}
    enabled: bool = True


# =============================================================================
# Request Models
# =============================================================================
class MessagesRequest(BaseModel):
    model_config = {"extra": "allow"}
    model: str
    max_tokens: int | None = None
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    stop_sequences: list[str] | None = None
    stream: bool | None = True
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    metadata: dict[str, Any] | None = None
    tools: list[Tool] | None = None
    tool_choice: dict[str, Any] | None = None
    thinking: ThinkingConfig | None = None
    extra_body: dict[str, Any] | None = None
    original_model: str | None = None
    resolved_provider_model: str | None = None

    @model_validator(mode="after")
    def map_model(self) -> MessagesRequest:
        """Map any Claude model name to the configured model (model-aware)."""
        # Extract system messages from the messages list
        self.messages, self.system = _extract_system_messages(self.messages, self.system)

        settings = get_settings()
        if self.original_model is None:
            self.original_model = self.model

        # Only resolve if not already explicitly set by routes
        if self.resolved_provider_model is None:
            resolved_full = settings.resolve_model(self.original_model)
            self.resolved_provider_model = resolved_full
            self.model = Settings.parse_model_name(resolved_full)
        else:
            self.model = Settings.parse_model_name(self.resolved_provider_model)

        if self.model != self.original_model:
            logger.debug(f"MODEL MAPPING: '{self.original_model}' -> '{self.model}'")

        return self



class TokenCountRequest(BaseModel):
    model: str
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    tools: list[Tool] | None = None
    thinking: ThinkingConfig | None = None
    tool_choice: dict[str, Any] | None = None

    @model_validator(mode="after")
    def normalize_request(self) -> TokenCountRequest:
        """Extract system messages and normalize request."""
        self.messages, self.system = _extract_system_messages(self.messages, self.system)
        return self

    @field_validator("model")
    @classmethod
    def validate_model_field(cls, v: str, info) -> str:
        """Map any Claude model name to the configured model (model-aware)."""
        settings = get_settings()
        resolved_full = settings.resolve_model(v)
        return Settings.parse_model_name(resolved_full)
