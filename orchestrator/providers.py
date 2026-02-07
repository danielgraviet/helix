"""LLM provider adapters — Anthropic and Cerebras (OpenAI-compatible)."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import config


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class AgentResponse:
    text_parts: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    is_done: bool = False
    raw_message: Any = None


class LLMProvider(ABC):
    @abstractmethod
    def create_message(self, system: str, messages: list, tools: list) -> AgentResponse:
        ...

    @abstractmethod
    def format_tool_results(self, tool_results: list[dict]) -> list[dict]:
        ...

    @abstractmethod
    def convert_tools(self, tools: list[dict]) -> list:
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL

    def convert_tools(self, tools: list[dict]) -> list[dict]:
        return tools

    def create_message(self, system: str, messages: list, tools: list) -> AgentResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            system=system,
            tools=tools,
            messages=messages,
        )

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        return AgentResponse(
            text_parts=text_parts,
            tool_calls=tool_calls,
            is_done=(response.stop_reason == "end_turn"),
            raw_message={"role": "assistant", "content": response.content},
        )

    def format_tool_results(self, tool_results: list[dict]) -> list[dict]:
        return [{"role": "user", "content": [
            {
                "type": "tool_result",
                "tool_use_id": tr["id"],
                "content": tr["content"],
            }
            for tr in tool_results
        ]}]


class CerebrasProvider(LLMProvider):
    def __init__(self):
        import openai
        self.client = openai.OpenAI(
            base_url=config.CEREBRAS_BASE_URL,
            api_key=config.CEREBRAS_API_KEY,
        )
        self.model = config.CEREBRAS_MODEL

    def convert_tools(self, tools: list[dict]) -> list[dict]:
        converted = []
        for tool in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })
        return converted

    def create_message(self, system: str, messages: list, tools: list) -> AgentResponse:
        openai_messages = [{"role": "system", "content": system}] + messages

        kwargs = {
            "model": self.model,
            "max_tokens": config.MAX_TOKENS,
            "messages": openai_messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        message = choice.message

        text_parts = [message.content] if message.content else []
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

        raw = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            raw["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        return AgentResponse(
            text_parts=text_parts,
            tool_calls=tool_calls,
            is_done=(choice.finish_reason == "stop"),
            raw_message=raw,
        )

    def format_tool_results(self, tool_results: list[dict]) -> list[dict]:
        return [
            {
                "role": "tool",
                "tool_call_id": tr["id"],
                "content": tr["content"],
            }
            for tr in tool_results
        ]


def get_provider() -> LLMProvider:
    if config.LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    elif config.LLM_PROVIDER == "cerebras":
        return CerebrasProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r}. Use 'anthropic' or 'cerebras'.")
