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
| List all | `Scan` | Full table read | See limitation below |
| Update fields | `UpdateItem` | Conditional — fails if deviceId absent | Returns updated item |
| Delete | `DeleteItem` | Conditional — fails if deviceId absent | Returns boolean |

### Scan Limitation

`GET /devices` currently uses a DynamoDB **Scan**, which reads every item in the
table and consumes read capacity proportional to the table size. This is acceptable
for a development dataset of fewer than ~1,000 items.

**Production scale solution:** Add a Global Secondary Index (GSI) on `type` or
`status` and replace Scan with a targeted Query. For a general "list all" use case
at scale, consider DynamoDB pagination with `Limit` + `LastEvaluatedKey` and expose
`limit` and `nextToken` query parameters on the API endpoint.

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
| ListDevices    | DynamoDBReadPolicy     | Scan                             |
| UpdateDevice   | DynamoDBCrudPolicy     | GetItem, PutItem, UpdateItem     |
| DeleteDevice   | DynamoDBCrudPolicy     | GetItem, DeleteItem              |

## Logging

Each function logs at `INFO` level by default. Set `LOG_LEVEL=DEBUG` in the SAM
template environment variables to increase verbosity without a code change. Every
log line includes the Lambda `aws_request_id` for cross-service correlation in
CloudWatch Logs Insights.
