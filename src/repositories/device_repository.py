import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from models.device import Device
from utils.logging_config import configure_logger

logger = configure_logger(__name__)


class DeviceRepository:
    def __init__(self):
        self._table_name = os.environ["DEVICES_TABLE"]
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def create(self, device: Device) -> Device:
        try:
            self._table.put_item(
                Item=device.to_item(),
                ConditionExpression="attribute_not_exists(deviceId)",
            )
            return device
        except ClientError as exc:
            logger.error("DynamoDB put_item failed: %s", exc.response["Error"])
            raise

    def get(self, device_id: str) -> Optional[Device]:
        try:
            response = self._table.get_item(Key={"deviceId": device_id})
            item = response.get("Item")
            if item is None:
                return None
            return Device.from_item(item)
        except ClientError as exc:
            logger.error("DynamoDB get_item failed: %s", exc.response["Error"])
            raise

    def list_all(self) -> list[Device]:
        # NOTE: Scan reads every item in the table.
        # Acceptable for dev with < 1,000 items; replace with GSI + Query at scale.
        try:
            response = self._table.scan()
            items = response.get("Items", [])
            while "LastEvaluatedKey" in response:
                response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))
            return [Device.from_item(item) for item in items]
        except ClientError as exc:
            logger.error("DynamoDB scan failed: %s", exc.response["Error"])
            raise

    def update(self, device_id: str, updates: dict) -> Optional[Device]:
        if not updates:
            return self.get(device_id)

        now = datetime.now(timezone.utc).isoformat()
        # Build a new dict — never mutate the caller's input.
        updates = {**updates, "updatedAt": now}

        update_expression_parts = []
        expression_attr_names = {}
        expression_attr_values = {}

        for i, (key, value) in enumerate(updates.items()):
            placeholder = f"#attr{i}"
            value_placeholder = f":val{i}"
            update_expression_parts.append(f"{placeholder} = {value_placeholder}")
            expression_attr_names[placeholder] = key
            expression_attr_values[value_placeholder] = value

        update_expression = "SET " + ", ".join(update_expression_parts)

        try:
            response = self._table.update_item(
                Key={"deviceId": device_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attr_names,
                ExpressionAttributeValues=expression_attr_values,
                ConditionExpression="attribute_exists(deviceId)",
                ReturnValues="ALL_NEW",
            )
            return Device.from_item(response["Attributes"])
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            logger.error("DynamoDB update_item failed: %s", exc.response["Error"])
            raise

    def delete(self, device_id: str) -> bool:
        try:
            self._table.delete_item(
                Key={"deviceId": device_id},
                ConditionExpression="attribute_exists(deviceId)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            logger.error("DynamoDB delete_item failed: %s", exc.response["Error"])
            raise
