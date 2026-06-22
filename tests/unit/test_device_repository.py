"""
Regression tests for DeviceRepository.

Covers correctness of DynamoDB operations and the immutability contract:
repository.update() must never mutate its caller's input dict.
"""
import pytest
from moto import mock_aws
from models.device import Device
from repositories.device_repository import DeviceRepository, DeviceAlreadyExistsError


@pytest.fixture
def repo(dynamodb_table) -> DeviceRepository:
    return DeviceRepository()


@pytest.fixture
def saved_device(repo) -> Device:
    device = Device(name="Fixture Sensor", type="sensor")
    return repo.create(device)


# ── create ────────────────────────────────────────────────────────────────


class TestCreate:
    def test_returns_device_with_generated_id(self, repo):
        device = Device(name="New Device", type="actuator")
        result = repo.create(device)
        assert result.device_id == device.device_id
        assert result.name == "New Device"

    def test_persists_to_dynamo(self, repo):
        device = Device(name="Persisted", type="gateway")
        repo.create(device)
        fetched = repo.get(device.device_id)
        assert fetched is not None
        assert fetched.name == "Persisted"

    def test_duplicate_device_id_raises(self, repo):
        device = Device(name="Dup", type="sensor")
        repo.create(device)
        with pytest.raises(DeviceAlreadyExistsError):
            repo.create(device)  # same deviceId — conditional write must reject


# ── get ───────────────────────────────────────────────────────────────────


class TestGet:
    def test_returns_none_for_missing_id(self, repo):
        result = repo.get("does-not-exist")
        assert result is None

    def test_returns_correct_device(self, repo, saved_device):
        result = repo.get(saved_device.device_id)
        assert result is not None
        assert result.device_id == saved_device.device_id
        assert result.name == saved_device.name


# ── list_paginated ──────────────────────────────────────────────────────────


class TestListPaginated:
    def test_returns_empty_list_initially(self, repo):
        items, last_key = repo.list_paginated(limit=25)
        assert items == []
        assert last_key is None

    def test_returns_all_items_when_under_limit(self, repo):
        repo.create(Device(name="A", type="sensor"))
        repo.create(Device(name="B", type="actuator"))
        items, last_key = repo.list_paginated(limit=25)
        assert len(items) == 2
        assert last_key is None
        assert {d.name for d in items} == {"A", "B"}

    def test_limit_caps_page_and_returns_cursor(self, repo):
        for i in range(5):
            repo.create(Device(name=f"D{i}", type="sensor"))
        items, last_key = repo.list_paginated(limit=2)
        assert len(items) == 2
        assert last_key is not None

    def test_cursor_walks_all_pages_without_duplicates(self, repo):
        for i in range(5):
            repo.create(Device(name=f"D{i}", type="sensor"))
        seen = []
        start_key = None
        while True:
            items, start_key = repo.list_paginated(limit=2, start_key=start_key)
            seen.extend(d.device_id for d in items)
            if not start_key:
                break
        assert len(seen) == 5
        assert len(set(seen)) == 5  # no duplicates across pages

    def test_query_by_type_filters_via_gsi(self, repo):
        repo.create(Device(name="S1", type="sensor"))
        repo.create(Device(name="S2", type="sensor"))
        repo.create(Device(name="G1", type="gateway"))
        items, _ = repo.list_paginated(limit=25, device_type="sensor")
        assert len(items) == 2
        assert all(d.type == "sensor" for d in items)

    def test_query_by_type_returns_empty_for_no_matches(self, repo):
        repo.create(Device(name="S1", type="sensor"))
        items, last_key = repo.list_paginated(limit=25, device_type="controller")
        assert items == []
        assert last_key is None


# ── update ────────────────────────────────────────────────────────────────


class TestUpdate:
    def test_updates_specified_field(self, repo, saved_device):
        result = repo.update(saved_device.device_id, {"status": "maintenance"})
        assert result is not None
        assert result.status == "maintenance"
        assert result.name == saved_device.name   # unchanged

    def test_returns_none_for_missing_device(self, repo):
        result = repo.update("no-such-id", {"status": "inactive"})
        assert result is None

    def test_updated_at_is_set(self, repo, saved_device):
        result = repo.update(saved_device.device_id, {"status": "inactive"})
        assert result is not None
        assert result.updated_at != ""

    # ── Mutation regression ───────────────────────────────────────────────

    def test_does_not_mutate_caller_dict(self, repo, saved_device):
        """
        Regression: repository.update() previously added 'updatedAt' directly
        into the caller's dict. This modifies caller-owned state and is a
        subtle source of bugs in handler logic written after the update call.
        """
        caller_payload = {"status": "inactive"}
        original_keys = set(caller_payload.keys())

        repo.update(saved_device.device_id, caller_payload)

        assert set(caller_payload.keys()) == original_keys, (
            "update() must not mutate the caller's input dict. "
            f"Extra keys added: {set(caller_payload.keys()) - original_keys}"
        )

    def test_caller_dict_values_unchanged(self, repo, saved_device):
        """Ensure values as well as keys are untouched."""
        caller_payload = {"name": "  Trimmed Name  ", "status": "maintenance"}
        original_copy = dict(caller_payload)

        repo.update(saved_device.device_id, caller_payload)

        assert caller_payload == original_copy

    def test_updated_at_injected_into_dynamo_not_caller(self, repo, saved_device):
        """updatedAt appears in the persisted item but not in the caller's dict."""
        caller_payload = {"status": "inactive"}
        repo.update(saved_device.device_id, caller_payload)

        refreshed = repo.get(saved_device.device_id)
        assert refreshed is not None
        assert refreshed.updated_at is not None
        assert "updatedAt" not in caller_payload


# ── delete ────────────────────────────────────────────────────────────────


class TestDelete:
    def test_deletes_existing_device(self, repo, saved_device):
        result = repo.delete(saved_device.device_id)
        assert result is True
        assert repo.get(saved_device.device_id) is None

    def test_returns_false_for_missing_device(self, repo):
        result = repo.delete("does-not-exist")
        assert result is False
