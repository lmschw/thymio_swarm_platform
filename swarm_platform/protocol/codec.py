import json
from dataclasses import asdict, is_dataclass
from typing import Any


def encode(msg: Any) -> str:
    """Serialize a message to a JSON string.

    Args:
        msg: The message to serialize. If it is a dataclass instance, it is
            converted to a dict first; otherwise it is passed to the JSON
            encoder as-is.

    Returns:
        The JSON-encoded representation of the message.
    """
    if is_dataclass(msg):
        return json.dumps(asdict(msg))
    return json.dumps(msg)


def decode(raw: str) -> Any:
    """Deserialize a JSON string back into a Python object.

    Args:
        raw: The JSON-encoded string to decode.

    Returns:
        The decoded Python object (e.g. dict, list, or primitive).
    """
    return json.loads(raw)