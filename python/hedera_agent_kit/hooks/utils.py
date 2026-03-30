from typing import Any


def stringify_recursive(obj: Any) -> Any:
    """
    Recursively converts objects to a log-friendly format.
    Handles Pydantic models, SDK objects, and bytes.

    Args:
        obj (Any): The object to stringify.

    Returns:
        Any: The stringified object.
    """
    # Handle None and primitives
    if obj is None or isinstance(obj, (int, float, bool, str)):
        return obj

    # Handle bytes/bytearray - convert to hex string
    if isinstance(obj, (bytes, bytearray)):
        return f"0x{obj.hex()}"

    # Handle SDK objects (AccountId, TokenId, TopicId, PublicKey, Hbar, etc.)
    # These are usually Pydantic models themselves, but we want them stringified.
    # We check for common SDK types or types that should be stringified.
    sdk_types = (
        "AccountId",
        "TokenId",
        "TopicId",
        "PublicKey",
        "Hbar",
        "ScheduleId",
        "ContractId",
        "Timestamp",
    )
    if obj.__class__.__name__ in sdk_types:
        return str(obj)

    # Handle Pydantic models (our parameter schemas)
    # We use dict(obj) for shallow conversion to preserve nested objects for our own recursion.
    if hasattr(obj, "__pydantic_model_complete__") or hasattr(obj, "model_fields"):
        return stringify_recursive(dict(obj))
    if hasattr(obj, "dict") and callable(obj.dict):
        # Fallback for Pydantic v1 if needed, though we prefer shallow
        return stringify_recursive(obj.dict())

    # Handle lists, tuples, sets
    if isinstance(obj, (list, tuple, set)):
        return [stringify_recursive(item) for item in obj]

    # Handle dictionaries
    if isinstance(obj, dict):
        return {
            str(key): stringify_recursive(value) for key, value in obj.items()
        }

    # Handle other objects with custom __str__
    if hasattr(obj, "__str__") and obj.__class__.__str__ is not object.__str__:
        return str(obj)

    # Fallback to str() for anything else
    return str(obj)
