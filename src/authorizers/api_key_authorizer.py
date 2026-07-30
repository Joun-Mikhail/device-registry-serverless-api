"""Lambda authorizer guarding the HTTP API with a shared API key.

API Gateway invokes this before any handler runs. It compares the caller's
``x-api-key`` header against a secret held in AWS Secrets Manager and returns the
HTTP API simple response, ``{"isAuthorized": bool}``.

Design notes:

* The expected key is never stored in the template, the repository, or a Lambda
  environment variable — only the secret's ARN is. The value is fetched at cold
  start and cached, so the common path costs nothing.
* Comparison is constant-time. A plain ``==`` returns as soon as two bytes differ,
  which leaks the length of the matching prefix to anyone able to time responses.
* Every failure path denies. A missing secret, an AWS error, or a malformed event
  results in ``isAuthorized: False`` rather than an exception, because an
  unhandled exception in an authorizer is a 500 that some clients retry, and
  because failing open here would defeat the point of the authorizer entirely.
* Neither the supplied key nor the expected key is ever logged.
"""

from __future__ import annotations

import hmac
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

from utils.logging import get_logger

logger = get_logger(__name__)

# botocore logs full request and response bodies at DEBUG. For GetSecretValue
# that body contains the secret in clear text, and LOG_LEVEL is operator-set in
# template.yaml — so turning on debug logging to chase an unrelated problem would
# otherwise write the API key into CloudWatch. Hold the AWS SDK loggers at INFO
# here regardless of the configured level.
for _wire_logger in ("botocore", "boto3", "urllib3", "s3transfer"):
    logging.getLogger(_wire_logger).setLevel(logging.INFO)

API_KEY_HEADER = "x-api-key"

# Re-read the secret periodically so a rotated key takes effect without a
# redeploy, while still keeping the steady-state cost at zero API calls.
CACHE_TTL_SECONDS = 300

_cached_key: str | None = None
_cached_at: float = 0.0
_secrets_client = None


def _client():
    """Construct the Secrets Manager client lazily, so importing is side-effect free."""
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client("secretsmanager")
    return _secrets_client


def _expected_key() -> str | None:
    """Return the configured API key, or None if it cannot be resolved.

    Returning None rather than raising keeps the failure path in one place: the
    caller denies, and the reason is logged without the value.
    """
    global _cached_key, _cached_at

    if _cached_key is not None and (time.monotonic() - _cached_at) < CACHE_TTL_SECONDS:
        return _cached_key

    secret_arn = os.environ.get("API_KEY_SECRET_ARN")
    if not secret_arn:
        logger.error("API_KEY_SECRET_ARN is not set; denying all requests.")
        return None

    try:
        response = _client().get_secret_value(SecretId=secret_arn)
    except ClientError as exc:
        logger.error("Could not read the API key secret: %s", exc.response["Error"]["Code"])
        return None

    secret = response.get("SecretString")
    if not secret:
        logger.error("The API key secret holds no string value; denying all requests.")
        return None

    _cached_key = secret
    _cached_at = time.monotonic()
    return _cached_key


def _presented_key(event: dict) -> str | None:
    """Pull the API key header out of the event, case-insensitively.

    API Gateway lowercases header names for HTTP API payload format 2.0, but the
    lookup does not depend on that being true.
    """
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        return None
    for name, value in headers.items():
        if isinstance(name, str) and name.lower() == API_KEY_HEADER:
            return value
    return None


def reset_cache() -> None:
    """Drop the cached secret and client. Used by tests to isolate cases."""
    global _cached_key, _cached_at, _secrets_client
    _cached_key = None
    _cached_at = 0.0
    _secrets_client = None


def handler(event: dict, context) -> dict:
    """Authorize a request. Returns the HTTP API simple response shape."""
    presented = _presented_key(event or {})
    if not presented:
        logger.info("Request denied: no %s header presented.", API_KEY_HEADER)
        return {"isAuthorized": False}

    expected = _expected_key()
    if expected is None:
        return {"isAuthorized": False}

    # Constant-time: compare_digest does not short-circuit on the first mismatch.
    authorized = hmac.compare_digest(presented, expected)
    if not authorized:
        logger.info("Request denied: the presented API key did not match.")
    return {"isAuthorized": authorized}
