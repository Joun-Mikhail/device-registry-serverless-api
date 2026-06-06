# Evidence: DynamoDB Table

## What to capture here

After deployment and at least one successful API request, replace this file with
screenshots of the DynamoDB table.

---

## Screenshots to take

### 1 — Table overview (`dynamodb-table-overview.png`)

1. Open [DynamoDB → Tables](https://eu-central-1.console.aws.amazon.com/dynamodbv2/home?region=eu-central-1#tables) in **eu-central-1**.
2. Click **device-registry-dev**.
3. Screenshot the **Overview** tab showing:
   - Table name: `device-registry-dev`
   - Partition key: `deviceId (S)`
   - Billing mode: On-demand (PAY_PER_REQUEST)
   - Table status: Active

### 2 — Table items (`dynamodb-items.png`)

1. Click **Explore table items**.
2. Screenshot the item list showing at least one device with all expected attributes:
   - `deviceId` (UUID string)
   - `name`
   - `type`
   - `status`
   - `createdAt` (ISO 8601 timestamp)
   - `updatedAt` (ISO 8601 timestamp)

### 3 — Item detail (`dynamodb-item-detail.png`)

1. Click on any item to expand it.
2. Screenshot the full attribute list for that item.

---

## What a stored item looks like

```json
{
  "deviceId": "a3f1c2d4-8b5e-4f9a-bc12-d3e4f5a6b7c8",
  "name": "Temperature Sensor A",
  "type": "sensor",
  "status": "active",
  "location": "Building B / Room 12",
  "metadata": {
    "firmware": "v2.1.0"
  },
  "createdAt": "2024-11-01T10:30:00.123456+00:00",
  "updatedAt": "2024-11-01T10:30:00.123456+00:00"
}
```

## Notes

- `location` and `metadata` are omitted from DynamoDB if not provided (sparse storage).
- `updatedAt` is always present and changes on every `PATCH` request.
- `createdAt` is immutable — set once on creation, never modified.
- The table uses `DeletionPolicy: Retain` in CloudFormation, so it survives a
  `sam delete` if you tear down the stack.
