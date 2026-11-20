"""The text of a provider's answer, whatever shape it arrives in.

A provider's message carries its answer as a string (most of them) or as a
list of content blocks (Anthropic-style, and OpenRouter's free models). The
chat's contract is a string - `ChatResponse.response` is typed as one, and a
list is not a string, so the blocks have to be flattened before they reach it.

This module is the ONE place that knows the shape, so a provider that answers
in blocks cannot turn a working chat into a 500.
"""

from typing import Any

__all__ = ["content_to_text"]


def content_to_text(content: Any) -> str:
    """The answer of a provider as plain text.

    A string is its own text. A list of blocks - `{"type": "text", "text": ...}`
    - is joined into the text those blocks carry; a block with no text (a tool
    call, an image) carries no answer and is left out. Anything else is
    rendered as text, because a chat shows text.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        content = [content]
    if isinstance(content, (list, tuple)):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
                elif isinstance(text, list):
                    parts.extend(part for part in text if isinstance(part, str))
            elif block is not None:
                parts.append(str(block))
        return "".join(parts)
    return str(content)
