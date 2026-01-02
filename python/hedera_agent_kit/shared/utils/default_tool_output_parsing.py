import json
from typing import Any, Dict, Union

from hedera_agent_kit.shared.models import (
    ReturnBytesToolResponse,
    ExecutedTransactionToolResponse,
)

ParserOutput = Dict[str, Union[Any, str]]


def transaction_tool_output_parser(raw_output: str) -> ParserOutput:
    """
    Parses the stringifies JSON output from a transaction-related tool.

    Handles three main cases:
    1. RETURN_BYTES mode: output contains 'bytes_data' (serialized transaction).
    2. EXECUTE_TRANSACTION mode: output contains 'raw' (RawTransactionResponse dict)
       and 'human_message' (ExecutedTransactionToolResponse dict).
    3. ERROR mode: output contains 'error' and 'human_message' without a 'type' field.
    """
    try:
        parsed_object: Dict[str, Any] = json.loads(raw_output)
    except json.JSONDecodeError as error:
        print(
            f"[transaction_tool_output_parser] Failed to parse JSON: {raw_output} {error}"
        )
        return {
            "raw": {
                "status": "PARSE_ERROR",
                "error": str(error),
                "originalOutput": raw_output,
            },
            "humanMessage": "Error: Failed to parse tool output. The output was malformed.",
        }

    # Handle RETURN_BYTES mode
    if (
        "bytes_data" in parsed_object
        and "type" in parsed_object
        and parsed_object["type"] == "return_bytes"
    ):
        try:
            return_bytes_response = ReturnBytesToolResponse.from_dict(parsed_object)
            return {
                "raw": return_bytes_response.to_dict(),
                "humanMessage": return_bytes_response.human_message,
            }
        except Exception as error:
            print(
                f"[transaction_tool_output_parser] Failed to reconstruct ReturnBytesToolResponse: {error}"
            )
            pass

    # Handle EXECUTE_TRANSACTION mode
    if (
        "raw" in parsed_object
        and "human_message" in parsed_object
        and isinstance(parsed_object["raw"], dict)
        and "type" in parsed_object
        and parsed_object["type"] == "executed_transaction"
    ):
        raw_data = parsed_object.pop("raw")
        human_message = parsed_object.pop("human_message")

        merged_raw = {**raw_data, **parsed_object}

        try:
            executed_response = ExecutedTransactionToolResponse.from_dict(parsed_object)
            return {
                "raw": executed_response.to_dict()["raw"],
                "humanMessage": executed_response.human_message,
            }
        except Exception:
            return {
                "raw": merged_raw,
                "humanMessage": human_message,
            }

    # Handle ERROR mode or simple query responses (flat structure with human_message)
    if "human_message" in parsed_object:
        human_message = parsed_object["human_message"]

        # Create raw data from all fields except human_message
        raw_data = {k: v for k, v in parsed_object.items() if k != "human_message"}

        return {
            "raw": raw_data,
            "humanMessage": human_message,
        }

    # Fallback for unknown format
    print(
        f"[transaction_tool_output_parser] Parsed object has unknown shape: {parsed_object}"
    )
    return {
        "raw": {
            "status": "PARSE_ERROR",
            "originalOutput": raw_output,
            "parsedObject": parsed_object,
        },
        "humanMessage": "Error: Parsed tool output had an unexpected format.",
    }


def untyped_query_output_parser(raw_output: str) -> ParserOutput:
    """
    A flexible output parser that handles both transaction and query tool outputs.

    Transaction tools return: {'raw': {...}, 'human_message': '...'}
    Query tools return: {'human_message': '...', 'error': null, ...other fields}
    """
    try:
        parsed_object: Dict[str, Any] = json.loads(raw_output)
    except json.JSONDecodeError as error:
        print(f"untyped_query_output_parser failed to parse JSON: {error}")
        return {
            "raw": {
                "status": "PARSE_ERROR",
                "error": str(error),
                "originalOutput": raw_output,
            },
            "humanMessage": "Error: Failed to parse tool output. The output was malformed.",
        }

    if not isinstance(parsed_object, dict):
        print(
            f"untyped_query_output_parser: Parsed object is not a dict: {type(parsed_object)}"
        )
        return {
            "raw": {
                "status": "PARSE_ERROR",
                "error": "Parsed object is not a dictionary",
                "originalOutput": raw_output,
            },
            "humanMessage": "Error: Tool output had an unexpected format.",
        }

    # Check if this is a transaction tool output (has both 'raw' and 'human_message')
    if "raw" in parsed_object and "human_message" in parsed_object:
        return {
            "raw": parsed_object["raw"],
            "humanMessage": parsed_object["human_message"],
        }

    # Handle query tool output (flat structure with 'human_message' at top level)
    if "human_message" in parsed_object:
        # Extract human_message and put everything else in raw
        human_message = parsed_object["human_message"]

        # Create a copy without human_message for the raw data
        raw_data = {k: v for k, v in parsed_object.items() if k != "human_message"}

        return {
            "raw": raw_data,
            "humanMessage": human_message,
        }

    # If neither structure matches, return an error
    print(
        f"untyped_query_output_parser: Parsed object missing expected keys. "
        f"Keys found: {list(parsed_object.keys())}"
    )
    return {
        "raw": {
            "status": "PARSE_ERROR",
            "error": "Parsed object missing 'raw' or 'human_message' key",
            "originalOutput": raw_output,
            "parsedObject": parsed_object,
        },
        "humanMessage": "Error: Tool output had an unexpected format.",
    }
