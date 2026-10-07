"""Gemini access (Vertex AI or the Gemini Developer API) with schema-constrained JSON output.

Every response is parsed and validated with Pydantic. If validation fails, the model
gets one corrective retry that includes the validation error. API errors propagate
so the agent can fall back to its offline planner for that step and say so in the UI.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .config import AgentSettings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class JsonLLM(Protocol):
    model: str

    def generate_json(self, *, system: str, prompt: str, schema: type[T],
                      image_png: bytes | None = None) -> tuple[T, dict]: ...


def inline_schema(model: type[BaseModel]) -> dict:
    """Pydantic JSON schema with every $ref inlined (no $defs) and titles removed."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                merged = copy.deepcopy(defs[name])
                extra = {k: v for k, v in node.items() if k != "$ref"}
                merged.update(extra)
                return resolve(merged)
            return {k: resolve(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def _extract_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    return t.strip()


class GeminiLLM:
    """Thin wrapper over google-genai's Client.models.generate_content."""

    def __init__(self, settings: AgentSettings):
        from google import genai
        from google.genai import types

        self._types = types
        self.settings = settings
        self.model = settings.model
        self._thinking_ok = True
        # The client reads GOOGLE_GENAI_USE_VERTEXAI / GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION
        # or GEMINI_API_KEY / GOOGLE_API_KEY from the environment.
        self.client = genai.Client(http_options=types.HttpOptions(timeout=int(settings.timeout_s * 1000)))

    def _config(self, system: str, schema: type[BaseModel], thinking: bool):
        types = self._types
        # Temperature stays at the model default: Google advises against lowering it for Gemini 3.
        kwargs: dict[str, Any] = {
            "system_instruction": system,
            "response_mime_type": "application/json",
            "response_json_schema": inline_schema(schema),
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
        if thinking and self.settings.thinking_level:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=self.settings.thinking_level)
        return types.GenerateContentConfig(**kwargs)

    def _call(self, contents: list, config):
        return self.client.models.generate_content(model=self.model, contents=contents, config=config)

    def generate_json(self, *, system: str, prompt: str, schema: type[T],
                      image_png: bytes | None = None) -> tuple[T, dict]:
        types = self._types
        parts = [types.Part.from_text(text=prompt)]
        if image_png:
            parts.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
        contents: list = [types.Content(role="user", parts=parts)]
        config = self._config(system, schema, thinking=self._thinking_ok)
        meta: dict = {"model": self.model, "attempts": 0, "latency_s": 0.0}
        last_error = ""
        for attempt in range(2):
            meta["attempts"] = attempt + 1
            t0 = time.perf_counter()
            try:
                try:
                    resp = self._call(contents, config)
                except Exception as exc:
                    # A model without thinking levels rejects thinking_config: retry once without it.
                    if self._thinking_ok and self.settings.thinking_level and "thinking" in str(exc).lower():
                        self._thinking_ok = False
                        config = self._config(system, schema, thinking=False)
                        resp = self._call(contents, config)
                    else:
                        raise
            except Exception as exc:  # network, auth, quota, invalid request
                raise LLMError(f"Gemini request failed: {type(exc).__name__}: {str(exc)[:300]}") from exc
            meta["latency_s"] += time.perf_counter() - t0
            usage = getattr(resp, "usage_metadata", None)
            if usage is not None:
                meta["input_tokens"] = meta.get("input_tokens", 0) + (getattr(usage, "prompt_token_count", 0) or 0)
                meta["output_tokens"] = meta.get("output_tokens", 0) + (getattr(usage, "candidates_token_count", 0) or 0)
            text = ""
            try:
                text = resp.text or ""
            except Exception:  # blocked / no candidates
                text = ""
            try:
                return schema.model_validate_json(_extract_json(text)), meta
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)[:800]
                contents = contents + [
                    types.Content(role="model", parts=[types.Part.from_text(text=text or "(empty)")]),
                    types.Content(role="user", parts=[types.Part.from_text(
                        text="Your previous reply did not validate against the required JSON schema:\n"
                             f"{last_error}\nReturn only corrected JSON that matches the schema.")]),
                ]
        raise LLMError(f"Gemini output failed schema validation twice: {last_error[:300]}")


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=float)
