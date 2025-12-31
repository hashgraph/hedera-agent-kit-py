"""Mirrornode message decoding utilities."""

import base64
from typing import List, Any, Dict, Union

from .types import TopicMessage


def decode_messages(
    messages: List[TopicMessage], encoding: str
) -> Union[List[Dict[str, Any]], List[TopicMessage]]:
    """Decode the base64 message content based on the specified encoding.

    Args:
        messages: The list of raw message dictionaries from the Mirror Node.
        encoding: The target encoding ('utf-8' or 'base64').
    Returns:
        A new list of messages with decoded 'message' fields (if encoding is 'utf-8').
    """
    if encoding == "base64":
        # Keep the original base64 encoding
        return messages

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
