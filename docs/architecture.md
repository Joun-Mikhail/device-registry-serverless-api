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
│  PUT    /devices/{id}     →  UpdateDeviceFunction           │
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

## CI/CD Pipeline

```
Developer
  │
  │  git push / manual trigger
  ▼
GitHub Actions (workflow_dispatch)
  │
  ├─ Job 1: Unit Tests
  │     pytest tests/unit/
  │     Coverage ≥ 80%
  │
  └─ Job 2: Deploy (depends on Job 1 passing)
        │
        ├─ OIDC → AWS STS AssumeRoleWithWebIdentity
        │           (no long-lived credentials stored)
        │
        ├─ sam build --parallel --cached
        │
        └─ sam deploy → CloudFormation changeset
                          stack: device-registry-dev
                          region: eu-central-1
```

## IAM Permissions (Least Privilege)

Each Lambda function is granted only the DynamoDB actions it needs:

| Function       | DynamoDB Policy        | Actions                          |
|----------------|------------------------|----------------------------------|
| CreateDevice   | DynamoDBWritePolicy    | PutItem                          |
| GetDevice      | DynamoDBReadPolicy     | GetItem                          |
| ListDevices    | DynamoDBReadPolicy     | Scan                             |
| UpdateDevice   | DynamoDBCrudPolicy     | GetItem, PutItem, UpdateItem     |
| DeleteDevice   | DynamoDBCrudPolicy     | GetItem, DeleteItem              |
