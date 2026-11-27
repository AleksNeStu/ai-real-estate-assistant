"""
The screen that keeps an instruction out of the buyer's memory (Task #151).

The buyer's memory is read back into the model's prompt. A stored fact is
therefore an INPUT to the model, and a fact that reads like an ORDER is a
prompt injection, not a fact - a hostile listing title can plant one in an
innocent buyer's memory.

One screen, two call sites:

* write time - the extractor runs every fact through :func:`screen_fact`
  before it is stored;
* read time - the block builder runs every stored fact through it again, so
  the rows written before this screen existed are filtered too.

The screen is deliberately blunt: a fact that talks TO THE ASSISTANT is
dropped, never rewritten. A lost preference is a smaller harm than an
instruction that reaches the model as one.
"""

import logging
import re
from typing import Optional

from utils.sanitization import CONTROL_CHARS_FILTER

logger = logging.getLogger(__name__)

# How long one fact may be. A fact is a sentence about a house, not a
# document - and every character of it is carried into a prompt.
MAX_FACT_CHARS = 200

# A note is the loosest kind, so it gets the tightest cap.
NOTE_MAX_CHARS = 120

# The kinds a fact can carry. Mirrors agents.memory_extractor.FACT_KINDS -
# a kind outside the set is not a note, so it gets the general cap.
NOTE_KIND = "note"

# The phrases that mean the text is talking to the assistant rather than
# about a property. Each one is matched case-insensitively on the whole
# content, so a payload cannot smuggle a phrase past the screen by burying
# it in a sentence.
_ADDRESSING_PATTERNS: tuple[re.Pattern[str], ...] = (
    # An order to ignore what came before.
    re.compile(r"\bignore\b", re.IGNORECASE),
    re.compile(r"\bdisregard\b", re.IGNORECASE),
    # An order to drop what the assistant knows.
    re.compile(
        r"\bforget\s+(?:everything|all|previous|prior)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bforget\s+(?:your|the)\s+(?:previous\s+|prior\s+)?"
        r"(?:instructions?|rules?|prompts?|memory|context|messages?)\b",
        re.IGNORECASE,
    ),
    # The assistant's own instructions, quoted back at it.
    re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(?:your|the)\s+(?:instructions?|prompts?|rules?)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bprint\s+(?:your|the)\b", re.IGNORECASE),
    re.compile(r"\breveal\b", re.IGNORECASE),
    re.compile(r"\boverride\b", re.IGNORECASE),
    # An order to the assistant about what to say.
    re.compile(
        r"\b(?:always|never)\s+"
        r"(?:tell|telling|say|saying|reply|respond|mention|reveal|disclose|"
        r"include|report|describe|present|recommend|state|output|write)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\btell\s+the\s+buyer\b", re.IGNORECASE),
    # "you must" - the second person, addressed at the model.
    re.compile(r"\byou\s+must\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+(?:now|no\s+longer|unrestricted|free)\b", re.IGNORECASE),
)

# A role marker: the payload pretends to be a message of the conversation.
_ROLE_MARKER_RE = re.compile(
    r"^\s*(?:system|assistant|user|developer|human|tool)\s*:",
    re.IGNORECASE | re.MULTILINE,
)

# The chat-template markers a payload uses to open a turn of its own.
_TEMPLATE_MARKER_RE = re.compile(r"<\|")

# A fenced code block: a payload that quotes code is quoting an instruction.
_CODE_FENCE_RE = re.compile(r"```")

# A link in a note is a link the model may follow.
_URL_RE = re.compile(r"https?://", re.IGNORECASE)


def _clean(content: str) -> str:
    """Strip the control characters and flatten the whitespace of a content."""
    text = content.translate(CONTROL_CHARS_FILTER)
    return " ".join(text.split())


def screen_fact(kind: str, content: str) -> Optional[str]:
    """
    Decide whether a fact may be stored, and how long it may be.

    Args:
        kind: The kind of the fact - a note is capped lower than the rest.
        content: The fact in its own words.

    Returns:
        The content to keep, or None when the fact must be dropped. A dropped
        fact is logged, never stored: the caller's job is to carry on without
        it.
    """
    if not isinstance(content, str):
        return None

    text = _clean(content)
    if not text:
        return None

    if is_an_instruction(text):
        logger.warning("Buyer memory: dropping a fact that talks to the assistant")
        return None

    if kind == NOTE_KIND and _URL_RE.search(text):
        logger.warning("Buyer memory: dropping a note that carries a link")
        return None

    cap = NOTE_MAX_CHARS if kind == NOTE_KIND else MAX_FACT_CHARS
    if len(text) > cap:
        text = text[:cap].rstrip()

    return text


def is_an_instruction(text: str) -> bool:
    """
    Whether the text is addressed at the assistant rather than at a subject.

    This is the ONE definition of the threat in the repo: the buyer's memory
    and the web research ask the same question, so a payload one screen
    misses is a payload the other one misses too.
    """
    if not isinstance(text, str):
        return False
    return _is_an_instruction(_clean(text))


def _is_an_instruction(text: str) -> bool:
    """Whether a fact is addressed at the assistant rather than at a house."""
    if _ROLE_MARKER_RE.search(text):
        return True
    if _TEMPLATE_MARKER_RE.search(text):
        return True
    if _CODE_FENCE_RE.search(text):
        return True
    if any(pattern.search(text) for pattern in _ADDRESSING_PATTERNS):
        return True
    return False
