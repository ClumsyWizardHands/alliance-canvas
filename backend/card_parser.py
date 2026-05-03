"""
Streaming parser for ```card fenced blocks.

Agents emit structured artifacts as fenced code blocks with the language tag
`card` containing JSON of shape `{type, card, data}`. The parser:

  1. Buffers incoming chunks of assistant content.
  2. Emits "token" events for any text outside a card fence.
  3. When a card fence closes, parses the JSON and emits a "card" event.
  4. If the JSON is malformed, falls back to emitting the raw block as a code
     fence so the user still sees something useful, plus a "card_parse_error"
     diagnostic event.

The parser is single-pass and tolerant of arbitrarily-chunked input: it holds
back the last few characters of safe-to-emit text in case a fence is being
split across chunks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator


_OPEN_FENCE = "```card"
_CLOSE_FENCE = "```"
# Hold back this many bytes from the end of the buffer when no fence is in
# progress, so a chunk boundary in the middle of "```card" can't trick us.
_HOLDBACK = 16


@dataclass
class CardStreamParser:
    buffer: str = ""
    processed_to: int = 0
    in_card: bool = False
    card_start: int = -1
    cards_emitted: list[dict] = field(default_factory=list)

    def feed(self, chunk: str) -> Iterator[dict]:
        self.buffer += chunk
        while True:
            if not self.in_card:
                idx = self.buffer.find(_OPEN_FENCE, self.processed_to)
                if idx == -1:
                    # No fence visible — emit safe prefix only
                    safe = max(self.processed_to, len(self.buffer) - _HOLDBACK)
                    if safe > self.processed_to:
                        yield {"type": "token", "content": self.buffer[self.processed_to:safe]}
                        self.processed_to = safe
                    return
                # Emit text up to the fence
                if idx > self.processed_to:
                    yield {"type": "token", "content": self.buffer[self.processed_to:idx]}
                # Skip past the open fence and optional newline
                cursor = idx + len(_OPEN_FENCE)
                if cursor < len(self.buffer) and self.buffer[cursor] == "\n":
                    cursor += 1
                self.processed_to = cursor
                self.card_start = cursor
                self.in_card = True
                yield {"type": "card_start"}
            else:
                idx = self.buffer.find(_CLOSE_FENCE, self.processed_to)
                if idx == -1:
                    return  # wait for more
                raw = self.buffer[self.card_start:idx]
                yield from self._emit_card(raw)
                cursor = idx + len(_CLOSE_FENCE)
                # Eat optional trailing newline so it doesn't show as a stray blank line
                if cursor < len(self.buffer) and self.buffer[cursor] == "\n":
                    cursor += 1
                self.processed_to = cursor
                self.in_card = False
                self.card_start = -1

    def flush(self) -> Iterator[dict]:
        """Flush any buffered safe-to-emit text at end of stream."""
        if self.in_card:
            # Card never closed — fall back to emitting raw as a code block
            raw = self.buffer[self.card_start:]
            yield {
                "type": "token",
                "content": "\n```\n" + raw.strip() + "\n```\n",
            }
            yield {
                "type": "card_parse_error",
                "error": "unclosed card fence at end of stream",
                "raw": raw[:500],
            }
            self.in_card = False
            self.processed_to = len(self.buffer)
        elif self.processed_to < len(self.buffer):
            yield {"type": "token", "content": self.buffer[self.processed_to:]}
            self.processed_to = len(self.buffer)

    def _emit_card(self, raw: str) -> Iterator[dict]:
        text = raw.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            yield {
                "type": "token",
                "content": "\n```\n" + text + "\n```\n",
            }
            yield {
                "type": "card_parse_error",
                "error": str(e),
                "raw": text[:500],
            }
            return
        # Normalize shape: accept either {type:"card", card:"X", data:{...}} or {card:"X", data:{...}}
        if isinstance(data, dict):
            card_name = data.get("card") or data.get("type")
            payload = data.get("data") if "data" in data else data
            if not card_name:
                yield {
                    "type": "card",
                    "card": "FallbackCard",
                    "data": payload,
                    "raw_json": text,
                }
                self.cards_emitted.append({"card": "FallbackCard", "data": payload})
                return
            event = {
                "type": "card",
                "card": card_name,
                "data": payload,
            }
            self.cards_emitted.append({"card": card_name, "data": payload})
            yield event
        else:
            yield {
                "type": "card_parse_error",
                "error": f"card JSON was not an object (got {type(data).__name__})",
                "raw": text[:500],
            }


def strip_cards_from_text(content: str) -> str:
    """Remove ```card ... ``` blocks from a finished assistant message
    (used when persisting plain-text content separately from cards)."""
    out: list[str] = []
    i = 0
    while i < len(content):
        op = content.find(_OPEN_FENCE, i)
        if op == -1:
            out.append(content[i:])
            break
        out.append(content[i:op])
        cl = content.find(_CLOSE_FENCE, op + len(_OPEN_FENCE))
        if cl == -1:
            break
        i = cl + len(_CLOSE_FENCE)
        if i < len(content) and content[i] == "\n":
            i += 1
    return "".join(out).strip()
