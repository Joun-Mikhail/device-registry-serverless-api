import base64
import json
from typing import Optional


def encode_token(last_evaluated_key: Optional[dict]) -> Optional[str]:
    """Encode a DynamoDB LastEvaluatedKey into an opaque, URL-safe cursor.

    Returns None when there is no further page (caller omits nextToken).
    """
    if not last_evaluated_key:
        return None
    raw = json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_token(token: Optional[str]) -> Optional[dict]:
    """Decode an opaque cursor back into a DynamoDB ExclusiveStartKey.

    Raises ValueError if the token is malformed, so the caller can return 400.
    """
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        key = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid nextToken.") from exc
    if not isinstance(key, dict):
        raise ValueError("Invalid nextToken.")
    return key
