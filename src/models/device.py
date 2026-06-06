import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional


VALID_TYPES = {"sensor", "actuator", "gateway", "controller"}
VALID_STATUSES = {"active", "inactive", "maintenance"}


@dataclass
class Device:
    name: str
    type: str
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "active"
    location: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_item(self) -> dict:
        """Serialize to DynamoDB item format."""
        item = {
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

    def to_response(self) -> dict:
        """Serialize to API response format."""
        return self.to_item()

    @classmethod
    def from_item(cls, item: dict) -> "Device":
        """Deserialize from DynamoDB item."""
        return cls(
            device_id=item["deviceId"],
            name=item["name"],
            type=item["type"],
            status=item.get("status", "active"),
            location=item.get("location"),
            metadata=item.get("metadata"),
            created_at=item["createdAt"],
            updated_at=item["updatedAt"],
        )
