# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
│              (Postman / curl / application)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              API Gateway HTTP API                           │
│                  (eu-central-1)                             │
│                                                             │
│  POST   /devices          →  CreateDeviceFunction           │
│  GET    /devices          →  ListDevicesFunction            │
│  GET    /devices/{id}     →  GetDeviceFunction              │
│  PATCH  /devices/{id}     →  UpdateDeviceFunction           │
│  DELETE /devices/{id}     →  DeleteDeviceFunction           │
└──────────┬──────────────────────────────────────────────────┘
           │ Invoke
           ▼
┌─────────────────────────────────────────────────────────────┐
│                 AWS Lambda Functions                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Handler Layer        (src/handlers/)                 │  │
│  │  – Parses HTTP event, calls validator, calls repo     │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Validation Layer     (src/validation/)               │  │
│  │  – Validates and sanitises request payloads           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Repository Layer     (src/repositories/)             │  │
│  │  – Encapsulates all DynamoDB operations               │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Model Layer          (src/models/)                   │  │
│  │  – Device dataclass + serialisation                   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────────────────────────────┘
           │ SDK calls
           ▼
┌─────────────────────────────────────────────────────────────┐
│              DynamoDB (PAY_PER_REQUEST)                     │
│               Table: device-registry-dev                    │
│               Partition key: deviceId (S)                   │
└─────────────────────────────────────────────────────────────┘

All Lambda logs → CloudWatch Log Groups (7-day retention)
```

## Request Lifecycle

```
Client
  │
  │  1. HTTPS request
  ▼
API Gateway HTTP API
  │
  │  2. Proxy event (JSON)
  ▼
Lambda Handler
  │
  ├─ 3. Parse & validate request body
  │       └─ 400 Bad Request if invalid
  │
  ├─ 4. Call Repository
  │       ├─ 404 Not Found if item missing
  │       └─ 500 Internal Error on unexpected failure
  │
  └─ 5. Return structured JSON response
```

## DynamoDB Access Patterns

| Operation | Method | DynamoDB Operation | Notes |
|---|---|---|---|
| Create | `PutItem` | Conditional — fails if deviceId exists | UUID collision guard |
| Get by ID | `GetItem` | Single item lookup by partition key | O(1) |
| List by type | `Query` | GSI `type-createdAt-index`, partition = `type` | Efficient, sorted by createdAt, paginated |
| List all | `Scan` | Full table read, bounded by `limit` per request | Paginated; see note below |
| Update fields | `UpdateItem` | Conditional — fails if deviceId absent | Returns updated item |
| Delete | `DeleteItem` | Conditional — fails if deviceId absent | Returns boolean |

### Global Secondary Index

```
Table: device-registry-dev
  Partition key: deviceId (S)

GSI: type-createdAt-index
  Partition key: type (S)
  Sort key:      createdAt (S)
  Projection:    ALL
```

`GET /devices?type=sensor` issues a **Query** against this GSI — it reads only
items of that type, returns them sorted by `createdAt`, and supports cursor
pagination. This replaces a full Scan for the common "filter by type" pattern.

### Pagination

All list responses are paginated:

- `limit` (1–100, default 25) caps items per page.
- The DynamoDB `LastEvaluatedKey` is base64-encoded into an opaque `nextToken`
  returned in the response; the client passes it back to fetch the next page.
- `nextToken` is omitted when there are no more results.

### Remaining Scan

The **unfiltered** `GET /devices` (no `type`) still uses a `Scan`, because a
Query requires a partition key. It is now bounded per request by `limit`, so a
single call never reads the whole table unpaginated. At larger scale this
unfiltered list would be served by a materialised index (e.g. a constant-value
GSI partition keyed on `createdAt`) to eliminate the Scan entirely.

## CI/CD Pipeline

```
Developer
  │
  │  Manual trigger (workflow_dispatch)
  ▼
GitHub Actions
  │
  ├─ Job 1: Unit Tests
  │     pip install (cached) → pytest tests/unit/
  │     Coverage ≥ 80% enforced
  │
  └─ Job 2: Deploy (depends on Job 1 passing)
        │
        ├─ OIDC → AWS STS AssumeRoleWithWebIdentity
        │           (no long-lived credentials stored in GitHub)
        │
        ├─ sam build --parallel --cached
        │
        └─ sam deploy → CloudFormation changeset
                          stack: device-registry-dev
                          region: eu-central-1
```

## IAM Permissions (Least Privilege)

Each Lambda function is granted only the DynamoDB actions it requires:

| Function       | DynamoDB Policy        | Actions                          |
|----------------|------------------------|----------------------------------|
| CreateDevice   | DynamoDBWritePolicy    | PutItem                          |
| GetDevice      | DynamoDBReadPolicy     | GetItem                          |
| ListDevices    | DynamoDBReadPolicy     | Query (GSI), Scan                |
| UpdateDevice   | DynamoDBCrudPolicy     | GetItem, PutItem, UpdateItem     |
| DeleteDevice   | DynamoDBCrudPolicy     | GetItem, DeleteItem              |

## Logging

Each function logs at `INFO` level by default. Set `LOG_LEVEL=DEBUG` in the SAM
template environment variables to increase verbosity without a code change. Every
log line includes the Lambda `aws_request_id` for cross-service correlation in
CloudWatch Logs Insights.
