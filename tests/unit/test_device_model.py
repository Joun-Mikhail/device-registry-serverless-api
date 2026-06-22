from models.device import Device, VALID_TYPES, VALID_STATUSES


def test_device_defaults():
    device = Device(name="Temp Sensor A", type="sensor")
    assert device.status == "active"
    assert device.location is None
    assert device.metadata is None
    assert device.device_id is not None
    assert device.created_at is not None
    assert device.updated_at is not None


def test_device_to_item_excludes_none_fields():
    device = Device(name="Gateway 01", type="gateway")
    item = device.to_item()
    assert "location" not in item
    assert "metadata" not in item


def test_device_to_item_includes_optional_fields_when_set():
    device = Device(
        name="Actuator B",
        type="actuator",
        location="Building A / Floor 2",
        metadata={"firmware": "v1.4.2"},
    )
    item = device.to_item()
    assert item["location"] == "Building A / Floor 2"
    assert item["metadata"] == {"firmware": "v1.4.2"}


def test_device_roundtrip():
    original = Device(
        name="Controller X",
        type="controller",
        status="maintenance",
        location="Data Centre",
    )
    restored = Device.from_item(original.to_item())
    assert restored.device_id == original.device_id
    assert restored.name == original.name
    assert restored.type == original.type
    assert restored.status == original.status
    assert restored.location == original.location


def test_valid_types_constant():
    assert "sensor" in VALID_TYPES
    assert "actuator" in VALID_TYPES
    assert "gateway" in VALID_TYPES
    assert "controller" in VALID_TYPES


def test_valid_statuses_constant():
    assert "active" in VALID_STATUSES
    assert "inactive" in VALID_STATUSES
    assert "maintenance" in VALID_STATUSES
