"""LLM module API schemas (HTTP requests/responses)."""

from datetime import datetime

from pydantic import BaseModel, Field


# Request schemas
class GenerateRequest(BaseModel):
    """Request to generate text."""

    prompt: str
    context: str | None = None
    persona: str = "default"
    max_tokens: int = 500


class SummarizeRequest(BaseModel):
    """Request to summarize text."""

    text: str
    max_chars: int = 1000


# Response schemas
class GenerateResponse(BaseModel):
    """Response with generated text."""

    text: str
    model: str
    tokens_used: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SummarizeResponse(BaseModel):
    """Response with summarized text."""

    summary: str
    original_length: int
    summary_length: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
