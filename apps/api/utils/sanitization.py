"""
Input sanitization utilities for security.

Provides functions to sanitize and validate user input to prevent:
- Control character injection
- Excessive input length
- HTML/JavaScript injection
- Path traversal attempts
"""

import re
from typing import Any, Dict, List

# Control characters (excluding common whitespace)
CONTROL_CHARS = bytearray(range(0x00, 0x20)) + bytearray(range(0x7F, 0xA0))
# Allow tab, newline, carriage return
ALLOWED_CONTROL = {0x09, 0x0A, 0x0D}
# Code-point -> None mapping for str.translate().
#
# This MUST be a mapping, not a bytes object: str.translate() looks a bytes
# table up by ordinal, so a 62-byte table silently rewrites every code point
# below 0x3E - which includes spaces, digits and punctuation - and mangles
# non-Latin text (see issue #377). Mapping code points to None removes only
# the control characters we intend to remove.
CONTROL_CHARS_FILTER: dict[int, None] = {
    cp: None for cp in CONTROL_CHARS if cp not in ALLOWED_CONTROL
}

# Max lengths for different input types
DEFAULT_MAX_LENGTH = 10_000
CHAT_MAX_LENGTH = 50_000
SEARCH_MAX_LENGTH = 1_000
EMAIL_MAX_LENGTH = 254
PROPERTY_ID_MAX_LENGTH = 100


def sanitize_string(
    input_str: str,
    max_length: int = DEFAULT_MAX_LENGTH,
    remove_html: bool = True,
    allow_control_chars: bool = False,
) -> str:
    """
    Sanitize a string input for security.

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        remove_html: Whether to remove HTML tags
        allow_control_chars: Whether to allow control characters (excluding tab, newline, CR)

    Returns:
        Sanitized string

    Raises:
        ValueError: If input exceeds max_length
    """
    if not isinstance(input_str, str):
        return ""

    # Check length
    if len(input_str) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")

    # Remove or filter control characters
    if not allow_control_chars:
        input_str = input_str.translate(CONTROL_CHARS_FILTER)

    # Remove HTML tags if requested
    if remove_html:
        input_str = _strip_html(input_str)

    # Remove excessive whitespace
    input_str = " ".join(input_str.split())

    return input_str


def _strip_html(input_str: str) -> str:
    """
    Strip HTML tags from string.

    Uses a simple regex-based approach. For more complex cases,
    consider using a proper HTML parser like bleach.

    Args:
        input_str: Input string potentially containing HTML

    Returns:
        String with HTML tags removed
    """
    # Remove script tags and content
    input_str = re.sub(
        r"<script\b[^>]*>(.*?)</script>", "", input_str, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove style tags and content
    input_str = re.sub(
        r"<style\b[^>]*>(.*?)</style>", "", input_str, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove HTML comments
    input_str = re.sub(r"<!--.*?-->", "", input_str, flags=re.DOTALL)

    # Remove remaining HTML tags
    input_str = re.sub(r"<[^>]+>", "", input_str)

    # Decode HTML entities
    import html

    try:
        input_str = html.unescape(input_str)
    except Exception:
        pass

    return input_str


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query input.

    Args:
        query: Search query string

    Returns:
        Sanitized query suitable for vector search

    Raises:
        ValueError: If query is invalid or too long
    """
    if not query:
        raise ValueError("Search query cannot be empty")

    return sanitize_string(
        query,
        max_length=SEARCH_MAX_LENGTH,
        remove_html=True,
        allow_control_chars=False,
    )


def sanitize_chat_message(message: str) -> str:
    """
    Sanitize chat message input.

    Args:
        message: Chat message string

    Returns:
        Sanitized message

    Raises:
        ValueError: If message is invalid or too long
    """
    if not message or not message.strip():
        raise ValueError("Chat message cannot be empty")

    return sanitize_string(
        message,
        max_length=CHAT_MAX_LENGTH,
        remove_html=False,  # Allow markdown formatting
        allow_control_chars=False,
    )


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email input.

    Args:
        email: Email address string

    Returns:
        Sanitized email

    Raises:
        ValueError: If email is invalid
    """
    if not email:
        return ""

    email = sanitize_string(email, max_length=EMAIL_MAX_LENGTH, remove_html=True)

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError(f"Invalid email format: {email}")

    return email.lower().strip()


def sanitize_property_id(property_id: str) -> str:
    """
    Sanitize property ID input.

    Args:
        property_id: Property identifier

    Returns:
        Sanitized property ID

    Raises:
        ValueError: If property_id is invalid
    """
    if not property_id:
        raise ValueError("Property ID cannot be empty")

    property_id = sanitize_string(
        property_id,
        max_length=PROPERTY_ID_MAX_LENGTH,
        remove_html=True,
        allow_control_chars=False,
    )

    # Remove any path traversal attempts
    property_id = property_id.replace("..", "").replace("\\", "").replace("/", "")

    if not property_id:
        raise ValueError("Property ID cannot be empty after sanitization")

    return property_id


def validate_json_fields(
    data: dict[str, Any], allowed_fields: set[str], max_field_length: int = 1000
) -> dict[str, Any]:
    """
    Validate JSON request body fields.

    Args:
        data: Request data dictionary
        allowed_fields: Set of allowed field names
        max_field_length: Maximum length for string field values

    Returns:
        Validated data dictionary

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")

    # Check for unexpected fields
    unexpected = set(data.keys()) - allowed_fields
    if unexpected:
        raise ValueError(f"Unexpected fields in request: {', '.join(unexpected)}")

    validated: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            if len(value) > max_field_length:
                raise ValueError(f"Field '{key}' exceeds maximum length")
            validated[key] = value.strip()
        elif isinstance(value, (int, float, bool, list, dict)):
            validated[key] = value
        else:
            raise ValueError(f"Field '{key}' has invalid type")

    return validated


def truncate_for_logging(value: str, max_length: int = 200) -> str:
    """
    Truncate a string for logging while preserving readability.

    Args:
        value: String to truncate
        max_length: Maximum length

    Returns:
        Truncated string with ellipsis if needed
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def sanitize_for_logging(value: Any, max_length: int = 500) -> str:
    """
    Sanitize a value for safe logging by stripping injection characters.

    Prevents log injection by removing newline, carriage return, and other
    control characters that could be used to forge log entries.

    Args:
        value: Any value to sanitize (converted to string)
        max_length: Maximum output length

    Returns:
        Sanitized string safe for logger calls
    """
    text = str(value)
    text = text.translate(CONTROL_CHARS_FILTER)
    text = text.replace("\n", " ").replace("\r", " ")
    return truncate_for_logging(text, max_length=max_length)


# Patterns for detecting sensitive data that should not be exposed
# IMPORTANT: Order matters - more specific patterns must come first
SENSITIVE_PATTERNS = [
    # OpenAI-style API keys (sk- prefix) - must come before generic pattern
    (r"sk-[a-zA-Z0-9-]+", "sk-***"),
    # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_ prefixes)
    (r"gh[pousr]_[a-zA-Z0-9-]+", "***"),
    # Generic API key patterns (for api_key=, token=, etc.)
    (
        r'(api[_-]?key|apikey|token|bearer|auth[_-]?token)(["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{7,})',
        r"\1\2***",
    ),
    # Bearer tokens
    (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer ***"),
    # Passwords (when preceded by key name)
    (r'(password|passwd|pwd)(["\']?\s*[:=]\s*["\']?)([^\s"\'`,<>]{6,})', r"\1\2***"),
    # Common test/placeholder passwords (for test data sanitization)
    (r"\b(password123|secret123|admin123|root123|test123|passwd123|secret)\b", "***"),
    # Email addresses (partial redaction)
    (r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", r"\1@***"),
    # URLs (redact query params which may contain sensitive data)
    (r"(https?://[^\s?]+)\?[^<>\s]*", r"\1?***"),
]


def redact_sensitive_data(data: Any) -> Any:
    """
    Redact sensitive data from tool intermediate steps and outputs.

    This prevents leaking:
    - API keys and tokens
    - Passwords
    - Email addresses (partially)
    - URLs with query parameters

    Args:
        data: Data to sanitize (can be dict, list, str, or other types)

    Returns:
        Sanitized data with sensitive values redacted
    """
    if isinstance(data, str):
        redacted = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        return redacted
    elif isinstance(data, dict):
        return {k: redact_sensitive_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    else:
        # For non-serializable objects, try to convert to string
        # This will raise errors for objects with broken __str__ methods
        try:
            str(data)
            return data
        except Exception:
            # Return placeholder for unserializable objects
            return "*** (sanitization failed)"


def sanitize_intermediate_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize intermediate tool steps to prevent leaking sensitive data.

    This function:
    1. Redacts API keys, tokens, passwords
    2. Redacts email addresses and URLs with query params
    3. Ensures all data is JSON-serializable
    4. Limits output size to prevent excessive memory usage

    Args:
        steps: List of intermediate step dictionaries from agent execution

    Returns:
        Sanitized list of intermediate steps safe for client transmission
    """
    if not steps:
        return []

    sanitized = []
    max_steps = 50  # Limit number of steps to prevent excessive output
    max_output_size = 1000  # Truncate long outputs

    for step in steps[:max_steps]:
        try:
            # Redact sensitive data
            safe_step = redact_sensitive_data(step)

            # Truncate long outputs
            if isinstance(safe_step, dict):
                for key, value in safe_step.items():
                    if isinstance(value, str) and len(value) > max_output_size:
                        safe_step[key] = value[:max_output_size] + "... (truncated)"
                    elif isinstance(value, (list, dict)):
                        # Convert complex objects to string representation
                        try:
                            serialized = str(value)
                            if len(serialized) > max_output_size:
                                safe_step[key] = serialized[:max_output_size] + "... (truncated)"
                        except Exception:
                            safe_step[key] = "... (unserializable)"

            sanitized.append(safe_step)
        except Exception:
            # If sanitization fails, include a placeholder instead of failing
            sanitized.append({"error": "Step sanitization failed"})

    return sanitized
