"""Mirrornode message decoding utilities."""

import base64
from typing import List, Any, Dict

from .types import TopicMessage


def decode_base64_messages(messages: List[TopicMessage]) -> List[Dict[str, Any]]:
    """Decode base64 message content to UTF-8 human-readable strings.

    Args:
        messages: The list of raw message dictionaries from the Mirror Node.
    Returns:
        A new list of messages with decoded 'message' fields.
    """
    decoded_messages = []
    for message in messages:
        new_message = dict(message)
        try:
            new_message["message"] = base64.b64decode(
                message.get("message", "")
            ).decode("utf-8")
        except Exception:
            # Keep original if decode fails
            pass
        decoded_messages.append(new_message)
    return decoded_messages
