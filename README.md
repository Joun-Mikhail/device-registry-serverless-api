# Serverless Device Registry API

A fully serverless REST API for registering and managing IoT devices. Built with AWS Lambda, API Gateway HTTP API, and DynamoDB. Deployed using AWS SAM with a GitHub Actions CI/CD pipeline.

---

## Overview

The Device Registry API provides CRUD operations over a device catalogue. Each device has a name, type, status, and optional location and metadata. The API is stateless — all state lives in DynamoDB, all compute in Lambda.

This project demonstrates:

- Structuring a Python Lambda project with clear separation of concerns (handlers, validation, repository, models)
- Writing Lambda functions that are testable in isolation using `moto`
- Deploying infrastructure as code with AWS SAM
- Authenticating GitHub Actions to AWS using OIDC (no stored credentials)
- Enforcing least-privilege IAM per function

---

## Architecture

```
Client (HTTP)
      │
      ▼
API Gateway HTTP API
      │
      ├── POST   /devices          → CreateDeviceFunction
      ├── GET    /devices          → ListDevicesFunction
      ├── GET    /devices/{id}     → GetDeviceFunction
      ├── PATCH  /devices/{id}     → UpdateDeviceFunction
      └── DELETE /devices/{id}    → DeleteDeviceFunction
                                         │
                                         ▼
                                  DynamoDB Table
                               (device-registry-dev)

All Lambda logs → CloudWatch Log Groups (7-day retention)
```

See [`docs/architecture.md`](docs/architecture.md) for detailed diagrams of the request lifecycle, CI/CD pipeline, DynamoDB access patterns, and IAM model.

---

## AWS Services Used

| Service | Purpose |
|---|---|
| **API Gateway HTTP API** | Routes HTTP requests to Lambda functions |
| **AWS Lambda** | Executes business logic per endpoint |
| **DynamoDB** | Persistent device storage (PAY\_PER\_REQUEST) |
| **CloudWatch Logs** | Structured logging with 7-day retention |
| **IAM** | Least-privilege execution roles per function |
| **AWS SAM** | Infrastructure as code and build tooling |
| **GitHub OIDC** | Keyless authentication from GitHub Actions to AWS |

---

## API Endpoints

All requests and responses use `Content-Type: application/json`.

All responses include CORS headers (`Access-Control-Allow-Origin: *`) to support browser-based clients in this development environment.

### Create a device

```
POST /devices
```

**Request body:**

```json
{
  "name": "Temperature Sensor A",
  "type": "sensor",
  "status": "active",
  "location": "Building B / Room 12",
  "metadata": { "firmware": "v2.1.0" }
}
```

`name` and `type` are required. `status` defaults to `active`.

**Response — 201 Created:**

```json
{
  "deviceId": "a3f1c2d4-...",
  "name": "Temperature Sensor A",
  "type": "sensor",
  "status": "active",
  "location": "Building B / Room 12",
  "metadata": { "firmware": "v2.1.0" },
  "createdAt": "2024-11-01T10:30:00+00:00",
  "updatedAt": "2024-11-01T10:30:00+00:00"
}
```

**Error response — 400 Bad Request:**

```json
{ "error": "'type' must be one of: ['actuator', 'controller', 'gateway', 'sensor']." }
```

---

### Get a device

```
GET /devices/{deviceId}
```

**Response — 200 OK** (same shape as above) or **404 Not Found:**

```json
{ "error": "Device not found." }
```

---

### List all devices

```
GET /devices
```

**Response — 200 OK:**

```json
{
  "items": [ { ... }, { ... } ],
  "count": 2
}
```

> **Note:** This endpoint uses a DynamoDB Scan operation, which reads every item in the table. It is suitable for development datasets of under ~1,000 devices. See [Architecture — Scan Limitation](docs/architecture.md) for the production-scale solution using GSI + Query.

---

### Update a device (partial)

```
PATCH /devices/{deviceId}
```

`PATCH` is used because this endpoint performs a **partial update** — only the fields provided in the request body are changed. Omitted fields retain their current values.

```json
{
  "status": "maintenance",
  "location": "Warehouse C"
}
```

**Response — 200 OK** (full updated device) or **404 Not Found**.

---

### Delete a device

```
DELETE /devices/{deviceId}
```

**Response — 200 OK:**

```json
{
  "message": "Device 'a3f1c2d4-...' deleted successfully."
}
```

Or **404 Not Found**.

---

## Data Model

| Field | Type | Required | Notes |
|---|---|---|---|
| `deviceId` | String (UUID) | Auto-generated | DynamoDB partition key |
| `name` | String | Yes | 1–100 characters |
| `type` | String | Yes | `sensor`, `actuator`, `gateway`, `controller` |
| `status` | String | No | `active` (default), `inactive`, `maintenance` |
| `location` | String | No | Up to 200 characters |
| `metadata` | Object | No | Free-form JSON object |
| `createdAt` | ISO 8601 timestamp | Auto-set | Set on creation, never modified |
| `updatedAt` | ISO 8601 timestamp | Auto-set | Updated on every write |

---

## Validation Rules

- `name` — required, non-empty string, max 100 characters
- `type` — required, must be one of: `sensor`, `actuator`, `gateway`, `controller`
- `status` — optional, must be one of: `active`, `inactive`, `maintenance`
- `location` — optional string, max 200 characters
- `metadata` — optional, must be a JSON object (not an array or scalar)
- PATCH requests must include at least one recognised field; unknown fields return `400`

---

## Testing

Tests use `pytest` and `moto` to mock DynamoDB locally — no AWS account needed.

```
tests/
├── conftest.py                    # Shared fixtures (mock DynamoDB table)
├── unit/
│   ├── test_device_model.py       # Device dataclass and serialisation
│   ├── test_device_validator.py   # Validation rules (create and update)
│   ├── test_handlers.py           # Handler logic end-to-end (mocked DB)
│   └── test_device_repository.py  # Repository operations + mutation regression
└── integration/
    └── test_api.py                # Live API tests (requires API_BASE_URL)
```

**Run unit tests:**

```bash
pip install -r requirements-dev.txt
pytest                  # uses pytest.ini defaults (tests/unit/, coverage ≥ 80%)
```

**Run integration tests against a deployed stack:**

```bash
export API_BASE_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
pytest tests/integration/ -v
```

**Postman collection:** [`docs/postman/device-registry.postman_collection.json`](docs/postman/device-registry.postman_collection.json)

Import into Postman, set the `base_url` collection variable, and run the requests in order. Each request includes automated test scripts that verify status codes and response shape.

---

## CI/CD Pipeline

The pipeline is triggered manually via `workflow_dispatch` in GitHub Actions.

**Stages:**

1. **Unit Tests** — installs deps (pip cache enabled), runs `pytest tests/unit/` with coverage enforcement (≥80%)
2. **Deploy** — runs only if tests pass; authenticates to AWS via GitHub OIDC, then:
   - `sam build --parallel --cached`
   - `sam deploy` to stack `device-registry-dev` in `eu-central-1`
   - Prints deployed stack outputs (API URL, table name)

No long-lived AWS credentials are stored in GitHub Secrets. Only `AWS_DEPLOY_ROLE_ARN` is stored (the ARN of the IAM role to assume via OIDC).

---

## Monitoring & Logging

Each Lambda function writes structured logs to a dedicated CloudWatch Log Group:

| Log Group | Retention |
|---|---|
| `/aws/lambda/device-registry-create-dev` | 7 days |
| `/aws/lambda/device-registry-get-dev` | 7 days |
| `/aws/lambda/device-registry-list-dev` | 7 days |
| `/aws/lambda/device-registry-update-dev` | 7 days |
| `/aws/lambda/device-registry-delete-dev` | 7 days |

Every log line includes the Lambda `aws_request_id` for correlation across log groups. Log verbosity is controlled by the `LOG_LEVEL` environment variable in the SAM template — set to `DEBUG` for detailed output without a code change.

Unhandled exceptions are logged with a full traceback before returning a generic `500` response — stack traces are never exposed to callers.

---

## Security Considerations

**No hardcoded credentials.** The `DEVICES_TABLE` environment variable is injected by SAM at deploy time from `!Ref DevicesTable`. AWS SDK credentials come from the Lambda execution role.

**Least-privilege IAM.** Each function is granted only the DynamoDB actions it requires (e.g. `CreateDevice` gets `PutItem` only, not `Scan` or `DeleteItem`).

**GitHub OIDC.** The CI/CD pipeline uses OIDC federation to assume an IAM role. No AWS access keys are stored in GitHub at any point.

**Input validation.** All user-supplied fields are validated for type, length, and allowed values before reaching the repository layer.

**Error isolation.** Internal error messages and stack traces are logged to CloudWatch but never returned to the caller.

**CloudWatch retention.** Log groups are set to 7-day retention to limit exposure of any sensitive data that may appear in logs.

**CORS.** Response headers include `Access-Control-Allow-Origin: *`. This is appropriate for a dev-only endpoint with no authentication. Restrict to a specific origin in a production environment with an auth layer.

---

## Deployment Instructions

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12
- AWS credentials with sufficient permissions to deploy CloudFormation, Lambda, DynamoDB, and API Gateway

### Manual deployment (first time)

```bash
sam build --parallel

sam deploy --guided
# Stack name:          device-registry-dev
# Region:              eu-central-1
# Parameter overrides: Environment=dev
```

SAM creates an S3 bucket for deployment artefacts automatically.

### Subsequent deployments

```bash
sam build --parallel --cached
sam deploy
```

Or trigger the GitHub Actions workflow via the **Actions** tab → **Deploy — Device Registry API** → **Run workflow**.

---

## Cleanup Instructions

```bash
sam delete --stack-name device-registry-dev --region eu-central-1
```

> **Note:** The DynamoDB table has `DeletionPolicy: Retain` and will not be deleted with the stack. Delete it manually in the AWS console if you no longer need the data.

---

## Future Improvements

The highest-priority improvements in order:

1. **Pagination on `GET /devices`** — expose `limit` and `nextToken` query parameters, backed by DynamoDB's `Limit` + `ExclusiveStartKey` scan pagination. This is the most important gap for production readiness.
2. **GSI for filtered listing** — add a Global Secondary Index on `type` to support `GET /devices?type=sensor` with a targeted `Query` instead of a full `Scan`.
3. **OpenAPI spec** — attach an OpenAPI 3.0 definition to API Gateway for auto-generated documentation and client SDK generation.
4. **Structured logging** — replace `logging` with [`aws-lambda-powertools`](https://docs.powertools.aws.dev/lambda/python/) for JSON-formatted logs and easier CloudWatch Insights querying.
5. **Dead-letter queues** — add Lambda DLQs if the API is extended with async/event-driven patterns.
