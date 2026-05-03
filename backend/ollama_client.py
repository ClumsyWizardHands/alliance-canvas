"""
Async HTTP wrapper for Ollama's /api/chat endpoint.

Streams tokens, surfaces tool calls, and exposes a simple `is_reachable` health
check. Uses httpx with explicit per-call timeouts because generation can take
minutes on a long context.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Any

import httpx

from .config import OLLAMA_HOST, OLLAMA_TIMEOUT


class OllamaError(RuntimeError):
    pass


async def is_reachable() -> tuple[bool, str]:
    """Return (ok, message). Used by /api/health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/version")
            r.raise_for_status()
            data = r.json()
            return True, f"Ollama {data.get('version', '?')} at {OLLAMA_HOST}"
    except Exception as e:
        return False, f"Ollama unreachable at {OLLAMA_HOST}: {e}"


async def list_models() -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{OLLAMA_HOST}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])


async def chat_stream(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    options: dict[str, Any] | None = None,
) -> AsyncIterator[dict]:
    """
    Stream Ollama chat responses.

    Yields each parsed JSON chunk from Ollama's NDJSON stream. Each chunk has
    shape {"message": {"role": "...", "content": "...", "tool_calls": [...]?}, "done": bool}.

    Tool calls in Ollama are not streamed token-by-token — they arrive as a single
    chunk where `message.tool_calls` is populated. The caller should detect this
    and execute the tool before re-calling chat_stream with the result appended
    as a `tool` role message.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
    if options:
        payload["options"] = options

    timeout = httpx.Timeout(OLLAMA_TIMEOUT, connect=10.0, read=OLLAMA_TIMEOUT, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise OllamaError(
                        f"Ollama returned {resp.status_code}: {body.decode('utf-8', errors='replace')[:500]}"
                    )
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPError as e:
            raise OllamaError(f"Ollama transport error: {e}") from e
