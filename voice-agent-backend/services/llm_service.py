from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import openai
from anthropic import AsyncAnthropic, AnthropicError

LOG = logging.getLogger(__name__)


def _load_openai() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    openai.api_key = api_key


def _load_anthropic() -> AsyncAnthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing for fallback")
    return AsyncAnthropic(api_key=api_key)


@dataclass
class ToolCallResult:
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    status: str = "pending"
    error: Optional[str] = None


class LLMService:
    """Wrapper around GPT-4 (OpenAI) with Claude/OpenRouter fallbacks."""

    def __init__(self, tool_schemas: List[Dict[str, Any]]) -> None:
        self._tool_schemas = tool_schemas
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self._fallback_provider = os.getenv("LLM_FALLBACK", "anthropic")
        _load_openai()
        self._anthropic: Optional[AsyncAnthropic] = None
        self._system_prompt = self._build_system_prompt()

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are Aida, a professional medical scheduling assistant."
            " Always verify the caller's phone number before booking or modifying appointments."
            " You have access to structured tools."
            " Ask clarifying questions when information is missing."
            " You must confirm appointment details before finalizing."
            " End every successful call with the end_conversation tool."
            " Maintain a friendly and concise tone."
        )

    async def run_completion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = [
            {"role": "system", "content": self._system_prompt},
            *messages,
        ]
        try:
            response = await openai.ChatCompletion.acreate(
                model=self._model,
                temperature=0.3,
                messages=payload,
                functions=self._tool_schemas,
                function_call="auto",
            )
            return response
        except openai.error.OpenAIError as exc:
            LOG.error("OpenAI error: %s", exc)
            if self._fallback_provider == "anthropic":
                return await self._anthropic_completion(messages)
            raise

    async def _anthropic_completion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self._anthropic:
            self._anthropic = _load_anthropic()
        try:
            response = await self._anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=600,
                system=self._system_prompt,
                messages=[
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in messages
                ],
            )
            # Normalize to ChatCompletion-like payload
            content = response.content[0].text if response.content else ""
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content,
                            "function_call": None,
                        }
                    }
                ],
                "usage": {"total_tokens": response.usage.total_tokens},
            }
        except AnthropicError as exc:
            LOG.error("Anthropic fallback failed: %s", exc)
            raise

    async def summarize_call(
        self,
        transcript: List[Dict[str, str]],
        appointments: List[Dict[str, Any]],
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        summary_prompt = (
            "Summarize the call in 3-5 bullet points, suitable for a CRM entry."
            " Include booked/modified/cancelled appointments with ISO datetimes."
            " Extract any explicit user preferences in JSON under key preferences."
            " Estimate a JSON cost_breakdown with stt_minutes, tts_characters, llm_tokens, total_usd."
        )
        response = await openai.ChatCompletion.acreate(
            model=self._model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": summary_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript": transcript,
                            "appointments": appointments,
                            "preferences": preferences,
                        }
                    ),
                },
            ],
        )
        content = response["choices"][0]["message"]["content"]
        return {
            "summary_text": content,
            "usage": response.get("usage", {}),
        }

    def build_tool_schema(self) -> List[Dict[str, Any]]:
        return self._tool_schemas

    @staticmethod
    def parse_tool_call(choice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        message = choice.get("message", {})
        call = message.get("function_call")
        if not call:
            return None
        arguments = json.loads(call.get("arguments") or "{}")
        return {
            "name": call.get("name"),
            "arguments": arguments,
        }
