"""Local Llama LLM Adapter.

Serves Llama 3.1/3.3 or Gemma via vLLM or Ollama for structured
generation in the ReAct loop and agent reasoning.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LocalLlamaAdapter:
    """Local LLM adapter via vLLM-compatible OpenAI API."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8001/v1",
        model: str = "meta-llama/Llama-3.3-70B-Instruct",
        temperature: float = 0.4,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.temperature = temperature
        self._client = httpx.Client(timeout=120.0)

    def generate(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate text via chat completions API."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
        }
        if json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"schema": json_schema},
            }

        response = self._client.post(
            f"{self.endpoint}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        """Generate structured output conforming to a Pydantic model."""
        schema = response_model.model_json_schema()
        raw = self.generate(messages, json_schema=schema)
        return response_model.model_validate_json(raw)
