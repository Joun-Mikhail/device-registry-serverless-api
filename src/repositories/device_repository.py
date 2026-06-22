import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from models.device import Device
from utils.logging import get_logger

logger = get_logger(__name__)

# GSI enabling efficient, sorted, paginated queries by device type.
TYPE_INDEX = "type-createdAt-index"


class DeviceAlreadyExistsError(Exception):
    """Raised when creating a device whose deviceId already exists."""


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
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise DeviceAlreadyExistsError(device.device_id) from exc
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

    def list_paginated(
        self,
        limit: int,
        start_key: Optional[dict] = None,
        device_type: Optional[str] = None,
    ) -> tuple[list[Device], Optional[dict]]:
        """Return one page of devices and the DynamoDB LastEvaluatedKey (or None).

        When `device_type` is given, the GSI is queried — an efficient, sorted
        (by createdAt) lookup that reads only matching items. When no type is
        given, a paginated Scan is used; this is the one remaining full-table
        read, bounded per request by `limit`. At larger scale the unfiltered
        list would be served by a materialised index instead of a Scan.
        """
        kwargs: dict = {"Limit": limit}
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key

        try:
            if device_type is not None:
                kwargs["IndexName"] = TYPE_INDEX
                kwargs["KeyConditionExpression"] = Key("type").eq(device_type)
                response = self._table.query(**kwargs)
            else:
                response = self._table.scan(**kwargs)
            items = [Device.from_item(item) for item in response.get("Items", [])]
            return items, response.get("LastEvaluatedKey")
        except ClientError as exc:
            logger.error("DynamoDB list failed: %s", exc.response["Error"])
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
