import pytest
from utils.pagination import encode_token, decode_token


class TestEncodeToken:
    def test_none_for_empty_key(self):
        assert encode_token(None) is None
        assert encode_token({}) is None

    def test_encodes_to_urlsafe_string(self):
        token = encode_token({"deviceId": "abc-123"})
        assert isinstance(token, str)
        # url-safe base64 contains no '+' or '/'
        assert "+" not in token and "/" not in token


class TestDecodeToken:
    def test_none_for_empty(self):
        assert decode_token(None) is None
        assert decode_token("") is None

    def test_roundtrip(self):
        key = {"deviceId": "abc-123", "createdAt": "2024-01-01T00:00:00+00:00"}
        assert decode_token(encode_token(key)) == key

    def test_malformed_raises_value_error(self):
        with pytest.raises(ValueError):
            decode_token("!!!not-base64!!!")

    def test_non_object_payload_raises(self):
        # base64 of the JSON number 42 — valid base64/JSON but not a dict
        import base64
        bad = base64.urlsafe_b64encode(b"42").decode("ascii")
        with pytest.raises(ValueError):
            decode_token(bad)
