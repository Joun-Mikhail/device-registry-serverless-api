"""The authorizer is the only thing standing between the internet and the API,
so these cover the denial paths as carefully as the success path."""

import boto3
import pytest
from moto import mock_aws

from authorizers import api_key_authorizer

SECRET_NAME = "device-registry/api-key-test"
GOOD_KEY = "s3cret-key-value"


@pytest.fixture
def api_key_secret(aws_credentials, monkeypatch):
    """Create the secret in a mocked Secrets Manager and point the module at it."""
    api_key_authorizer.reset_cache()
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="eu-central-1")
        arn = client.create_secret(Name=SECRET_NAME, SecretString=GOOD_KEY)["ARN"]
        monkeypatch.setenv("API_KEY_SECRET_ARN", arn)
        yield arn
    api_key_authorizer.reset_cache()


def _event(headers):
    return {"headers": headers, "routeArn": "arn:aws:execute-api:eu-central-1:1:api/dev/GET/devices"}


class TestAuthorized:
    def test_allows_a_request_presenting_the_correct_key(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)
        assert result == {"isAuthorized": True}

    def test_header_name_is_matched_case_insensitively(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"X-Api-Key": GOOD_KEY}), None)
        assert result == {"isAuthorized": True}


class TestDenied:
    def test_denies_a_wrong_key(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"x-api-key": "wrong"}), None)
        assert result == {"isAuthorized": False}

    def test_denies_when_the_header_is_absent(self, api_key_secret):
        assert api_key_authorizer.handler(_event({}), None) == {"isAuthorized": False}

    def test_denies_when_the_header_is_empty(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"x-api-key": ""}), None)
        assert result == {"isAuthorized": False}

    def test_denies_a_key_that_is_a_prefix_of_the_real_one(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY[:-1]}), None)
        assert result == {"isAuthorized": False}

    def test_denies_a_key_with_the_real_one_as_a_prefix(self, api_key_secret):
        result = api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY + "x"}), None)
        assert result == {"isAuthorized": False}


class TestFailsClosed:
    """Any misconfiguration must deny rather than raise or allow."""

    def test_denies_when_the_secret_arn_is_not_configured(self, aws_credentials, monkeypatch):
        api_key_authorizer.reset_cache()
        monkeypatch.delenv("API_KEY_SECRET_ARN", raising=False)
        result = api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)
        assert result == {"isAuthorized": False}

    def test_denies_when_the_secret_does_not_exist(self, aws_credentials, monkeypatch):
        api_key_authorizer.reset_cache()
        with mock_aws():
            monkeypatch.setenv("API_KEY_SECRET_ARN", "does-not-exist")
            result = api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)
        api_key_authorizer.reset_cache()
        assert result == {"isAuthorized": False}

    def test_denies_a_malformed_event_without_raising(self, api_key_secret):
        assert api_key_authorizer.handler({}, None) == {"isAuthorized": False}
        assert api_key_authorizer.handler({"headers": None}, None) == {"isAuthorized": False}
        assert api_key_authorizer.handler({"headers": "nonsense"}, None) == {"isAuthorized": False}


class TestSecretHandling:
    def test_the_secret_is_fetched_once_and_then_cached(self, api_key_secret, monkeypatch):
        calls = []
        real_client = api_key_authorizer._client()

        class CountingClient:
            def get_secret_value(self, **kwargs):
                calls.append(kwargs)
                return real_client.get_secret_value(**kwargs)

        monkeypatch.setattr(api_key_authorizer, "_secrets_client", CountingClient())
        api_key_authorizer._cached_key = None

        for _ in range(3):
            api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)

        assert len(calls) == 1, "the secret should be read once and served from cache after"

    def test_the_authorizer_never_logs_either_key(self, api_key_secret, caplog):
        with caplog.at_level("DEBUG", logger="authorizers.api_key_authorizer"):
            api_key_authorizer.handler(_event({"x-api-key": "a-wrong-but-secret-value"}), None)
            api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)
        emitted = "\n".join(r.getMessage() for r in caplog.records)
        assert GOOD_KEY not in emitted
        assert "a-wrong-but-secret-value" not in emitted

    def test_debug_logging_does_not_leak_the_secret_via_the_aws_sdk(self, api_key_secret, caplog):
        """botocore logs response bodies at DEBUG, and GetSecretValue's body holds
        the key in clear text. LOG_LEVEL is operator-controlled, so the module pins
        the SDK loggers to INFO to keep the secret out of CloudWatch."""
        api_key_authorizer.reset_cache()
        with caplog.at_level("DEBUG"):
            api_key_authorizer.handler(_event({"x-api-key": GOOD_KEY}), None)
        emitted = "\n".join(r.getMessage() for r in caplog.records)
        assert GOOD_KEY not in emitted, "the API key reached the logs via the AWS SDK"
