"""The tool calls of an answer, as data.

The chat draws a card per tool call. Until now the card was drawn by a
parser on the client that read the agent's stringified steps and guessed
what they meant. The steps still travel - other clients read them - but the
stream's meta event now also carries the calls as DATA: the tool's name,
the arguments it was called with, what it answered, and the sources it read.

This module is the ONE place that turns a step into a call, so the chat's
cards and the tools console talk about a call the same way.
"""

from typing import Any, Optional

from utils.sanitization import redact_sensitive_data

# The arguments and the result are the model's own text, and a tool can
# return a document. The card shows them; they are cut so a single call
# cannot fill the stream.
MAX_ARGS_CHARS = 2000
MAX_RESULT_CHARS = 4000

# The keys a step may carry. The agent's own steps are dicts; the web
# research agent's are dicts too, with their own spelling.
NAME_KEYS = ("tool", "name", "tool_name", "action")
ARGS_KEYS = ("tool_input", "args", "arguments", "input", "parameters")
RESULT_KEYS = ("observation", "result", "output", "content", "return", "value")


def _first(record: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _as_text(value: Any, limit: int) -> Optional[str]:
    """A value as the card shows it: text, cut to the limit."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    elif isinstance(value, (dict, list)):
        import json

        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    else:
        text = str(value)

    text = redact_sensitive_data(text)
    if not isinstance(text, str):
        text = str(text)
    if len(text) > limit:
        text = text[:limit] + "... (truncated)"
    return text


def build_tool_call(
    name: Any,
    args: Any = None,
    result: Any = None,
    sources: Any = None,
) -> Optional[dict]:
    """One tool call, as the client receives it.

    A call without a name is not a call - it is a note - and is dropped
    rather than guessed at.
    """
    if not isinstance(name, str) or not name.strip():
        return None

    call: dict = {"name": name.strip()}

    arguments = _as_text(args, MAX_ARGS_CHARS)
    if arguments is not None:
        call["args"] = arguments

    answer = _as_text(result, MAX_RESULT_CHARS)
    if answer is not None:
        call["result"] = answer

    if isinstance(sources, list):
        clean = [s for s in sources if isinstance(s, dict)]
        if clean:
            call["sources"] = clean

    return call


def build_tool_calls_from_steps(steps: Any) -> list[dict]:
    """Every tool call of a trace, in the order the agent made them.

    A step arrives in one of three shapes: the agent's own step - a pair of
    (action, observation) - the web research agent's dict, or the string
    repr of a step. The repr is the CLIENT's business: this function only
    builds what it can read as data, and the client falls back to its parser
    for the rest.
    """
    if not isinstance(steps, list):
        return []

    calls: list[dict] = []

    for step in steps:
        if isinstance(step, (tuple, list)) and len(step) == 2:
            action, observation = step
            name = getattr(action, "tool", None)
            args = getattr(action, "tool_input", None)
            if isinstance(action, dict):
                name = _first(action, NAME_KEYS)
                args = _first(action, ARGS_KEYS)
            call = build_tool_call(name, args, observation)
            if call:
                calls.append(call)
            continue

        if isinstance(step, dict):
            call = build_tool_call(
                _first(step, NAME_KEYS),
                _first(step, ARGS_KEYS),
                _first(step, RESULT_KEYS),
                step.get("sources"),
            )
            if call:
                calls.append(call)

    return calls
