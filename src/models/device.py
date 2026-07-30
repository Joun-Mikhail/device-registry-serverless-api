import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

VALID_TYPES = {"sensor", "actuator", "gateway", "controller"}
VALID_STATUSES = {"active", "inactive", "maintenance"}

# Applied when a caller omits 'status' on create, and when reading a legacy item
# written before 'status' was persisted.
DEFAULT_STATUS = "active"


@dataclass
class Device:
    name: str
    type: str
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = DEFAULT_STATUS
    location: str | None = None
    metadata: dict | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_item(self) -> dict[str, Any]:
        """Serialize to DynamoDB item format."""
        # Values are heterogeneous: metadata is a nested object, the rest are strings.
        item: dict[str, Any] = {
            "deviceId": self.device_id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.location is not None:
            item["location"] = self.location
        if self.metadata is not None:
            item["metadata"] = self.metadata
        return item

    def to_response(self) -> dict[str, Any]:
        """Serialize to API response format."""
        return self.to_item()

    @classmethod
    def from_item(cls, item: dict) -> "Device":
        """Deserialize from DynamoDB item."""
        return cls(
            device_id=item["deviceId"],
            name=item["name"],
            type=item["type"],
            status=item.get("status", DEFAULT_STATUS),
            location=item.get("location"),
            metadata=item.get("metadata"),
            created_at=item["createdAt"],
            updated_at=item["updatedAt"],
        )
