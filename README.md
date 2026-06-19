# Serverless Device Registry API

[![CI](https://github.com/Joun-Mikhail/device-registry-serverless-api/actions/workflows/deploy.yml/badge.svg)](https://github.com/Joun-Mikhail/device-registry-serverless-api/actions/workflows/deploy.yml)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](https://github.com/Joun-Mikhail/device-registry-serverless-api)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> A REST API for registering and managing IoT devices, built with production-style
> patterns and deployed as a single `dev` environment.
> Built with Python, AWS Lambda, API Gateway HTTP API, and DynamoDB.
> Deployed via AWS SAM with a GitHub Actions CI/CD pipeline using OIDC authentication.

---

## Overview

The Device Registry API provides CRUD operations over a catalogue of IoT devices.
Each device has a name, type, status, and optional location and metadata. The service
is fully stateless — all state lives in DynamoDB, all compute in Lambda.

**What this project demonstrates:**

| Area | Implementation |
|---|---|
| Serverless architecture | Lambda + API Gateway HTTP API + DynamoDB |
| Infrastructure as code | AWS SAM (`template.yaml`) |
| CI/CD | GitHub Actions with keyless OIDC authentication |
| Least-privilege IAM | Per-function DynamoDB policies (Read / Write / Crud) |
| Testability | `moto`-backed unit tests, zero AWS account required |
| Code quality | Layered architecture: handlers → validation → repository → model |
| Observability | CloudWatch log groups with 7-day retention, request ID correlation |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Client (Postman / curl / application)                               │
└─────────────────────────┬────────────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  API Gateway HTTP API  (eu-central-1)                                │
│                                                                      │
│   POST   /devices              → CreateDeviceFunction                │
│   GET    /devices              → ListDevicesFunction                 │
│   GET    /devices/{deviceId}   → GetDeviceFunction                   │
│   PATCH  /devices/{deviceId}   → UpdateDeviceFunction                │
│   DELETE /devices/{deviceId}   → DeleteDeviceFunction                │
└──────────┬───────────────────────────────────────────────────────────┘
           │ Lambda invoke
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Lambda Functions  (Python 3.12, 128 MB, 10 s timeout)              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  handlers/       Parse event → validate → call repository   │    │
│  │  validation/     Type checks, length limits, enum guards     │    │
│  │  repositories/   DynamoDB operations (conditional writes)    │    │
│  │  models/         Device dataclass + serialisation            │    │
│  │  utils/          Shared logging (LOG_LEVEL env var) + HTTP   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────┬───────────────────────────────────────────────────────────┘
           │ boto3
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DynamoDB  (PAY_PER_REQUEST)                                         │
│  Table: device-registry-dev    Partition key: deviceId (S)           │
└──────────────────────────────────────────────────────────────────────┘

All Lambda logs → CloudWatch Log Groups  (7-day retention)
```

See [`docs/architecture.md`](docs/architecture.md) for the request lifecycle,
CI/CD pipeline diagram, DynamoDB access patterns, and IAM model.

---

## Quick Start (local tests — no AWS required)

```bash
git clone https://github.com/Joun-Mikhail/device-registry-serverless-api.git
cd device-registry-serverless-api

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
pytest
```

Expected output: `59 passed, coverage 87%`.

---

## API Endpoints

All requests and responses use `Content-Type: application/json`.
Responses include CORS headers (`Access-Control-Allow-Origin: *`).

### Create a device — `POST /devices`

```bash
curl -X POST https://<api-url>/dev/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Temp Sensor A", "type": "sensor", "location": "Floor 2"}'
```

**201 Created:**
```json
{
  "deviceId": "a3f1c2d4-8b5e-4f9a-bc12-d3e4f5a6b7c8",
  "name": "Temp Sensor A",
  "type": "sensor",
  "status": "active",
  "location": "Floor 2",
  "createdAt": "2024-11-01T10:30:00.123456+00:00",
  "updatedAt": "2024-11-01T10:30:00.123456+00:00"
}
```

**400 Bad Request (validation failure):**
```json
{ "error": "'type' must be one of: ['actuator', 'controller', 'gateway', 'sensor']." }
```

---

### Get a device — `GET /devices/{deviceId}`

```bash
curl https://<api-url>/dev/devices/a3f1c2d4-8b5e-4f9a-bc12-d3e4f5a6b7c8
```

**200 OK** (device object) or **404 Not Found:**
```json
{ "error": "Device not found." }
```

---

### List all devices — `GET /devices`

```bash
curl https://<api-url>/dev/devices
```

**200 OK:**
```json
{ "items": [ { ... } ], "count": 1 }
```

> `GET /devices` uses a DynamoDB Scan — suitable for dev datasets under ~1,000 items.
> See [Architecture — Scan Limitation](docs/architecture.md) for the production solution.

---

### Update a device — `PATCH /devices/{deviceId}`

`PATCH` performs a **partial update** — only the fields provided are changed.

```bash
curl -X PATCH https://<api-url>/dev/devices/a3f1c2d4-... \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}'
```

**200 OK** (full updated device) or **404 Not Found**.

---

### Delete a device — `DELETE /devices/{deviceId}`

```bash
curl -X DELETE https://<api-url>/dev/devices/a3f1c2d4-...
```

**200 OK:**
```json
{ "message": "Device 'a3f1c2d4-...' deleted successfully." }
```

---

## Data Model

| Field | Type | Required | Notes |
|---|---|---|---|
| `deviceId` | String (UUID v4) | Auto-generated | DynamoDB partition key |
| `name` | String | **Yes** | 1–100 characters |
| `type` | String | **Yes** | `sensor` `actuator` `gateway` `controller` |
| `status` | String | No | `active` (default) `inactive` `maintenance` |
| `location` | String | No | Max 200 characters |
| `metadata` | Object | No | Free-form JSON — omitted from DB if not provided |
| `createdAt` | ISO 8601 | Auto-set | Immutable — never changes after creation |
| `updatedAt` | ISO 8601 | Auto-set | Updated on every write |

---

## Validation Rules

- `name` — required, non-empty, max 100 characters; leading/trailing whitespace trimmed
- `type` — required, enum: `sensor` | `actuator` | `gateway` | `controller`
- `status` — optional, enum: `active` | `inactive` | `maintenance`; defaults to `active`
- `location` — optional string, max 200 characters
- `metadata` — optional JSON object (arrays and scalars are rejected)
- PATCH requests must include at least one known field; unknown fields return `400`

---

## Testing

```
tests/
├── conftest.py                      Shared fixtures (mock DynamoDB via moto)
├── unit/
│   ├── test_device_model.py         Dataclass serialisation (6 tests)
│   ├── test_device_validator.py     Validation rules — create and update (17 tests)
│   ├── test_device_repository.py    DynamoDB operations + mutation regression (14 tests)
│   └── test_handlers.py             End-to-end handler logic, mocked DB (22 tests)
└── integration/
    └── test_api.py                  Live API tests — skip if API_BASE_URL unset
```

**Run unit tests:**
```bash
pytest                              # uses pytest.ini defaults
pytest tests/unit/ -v               # verbose
pytest --cov=src --cov-report=html  # HTML coverage report
```

**Run integration tests:**
```bash
export API_BASE_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
pytest tests/integration/ -v
```

**Postman collection:** [`docs/postman/device-registry.postman_collection.json`](docs/postman/device-registry.postman_collection.json)

Import into Postman, set `base_url`, run in order. Each request includes automated
test assertions (status codes + response shape).

---

## CI/CD Pipeline

Triggered manually via **Actions → Deploy — Device Registry API → Run workflow**.

```
┌─ Job 1: Unit Tests ──────────────────────────────────────────────────┐
│  pip install (cached) → pytest tests/unit/ → coverage ≥ 80% check   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ on success
┌─ Job 2: Build & Deploy ───────────▼───────────────────────────────────┐
│  OIDC → AssumeRoleWithWebIdentity (no stored AWS keys)                │
│  sam build --parallel --cached                                        │
│  sam deploy → CloudFormation changeset → device-registry-dev          │
│  Print ApiBaseUrl, DevicesTableName, DevicesTableArn                  │
└──────────────────────────────────────────────────────────────────────┘
```

**First-time setup:** see [`docs/oidc-setup.md`](docs/oidc-setup.md) for the IAM
role and GitHub secret configuration.

---

## Monitoring & Logging

| CloudWatch Log Group | Retention |
|---|---|
| `/aws/lambda/device-registry-create-dev` | 7 days |
| `/aws/lambda/device-registry-get-dev` | 7 days |
| `/aws/lambda/device-registry-list-dev` | 7 days |
| `/aws/lambda/device-registry-update-dev` | 7 days |
| `/aws/lambda/device-registry-delete-dev` | 7 days |

Every log line includes the Lambda `aws_request_id`, enabling cross-log correlation
in CloudWatch Logs Insights. Log verbosity is controlled by the `LOG_LEVEL`
environment variable in `template.yaml` — set to `DEBUG` without a code change.

---

## Security

| Control | Implementation |
|---|---|
| No stored AWS keys | GitHub OIDC federation (`AssumeRoleWithWebIdentity`) |
| Least-privilege IAM | Per-function DynamoDB policy (Write / Read / Crud only) |
| Input validation | Type, length, and enum checks before any DB operation |
| Error isolation | Stack traces logged to CloudWatch, never returned to callers |
| Secrets in code | None — `DEVICES_TABLE` injected by SAM at deploy time |
| Log retention | 7-day CloudWatch retention limits data exposure window |
| CORS | `Access-Control-Allow-Origin: *` — dev-only; restrict in production |
| **API authentication** | **None yet — the HTTP API is currently open (no authorizer).** Acceptable for a non-public `dev` environment; see Future Improvements item 1 before any public exposure. |

---

## Deployment

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) ≥ 1.100
- Python 3.12
- AWS credentials (for manual deploy) or OIDC role configured (for CI)

### First deployment

```bash
sam build --parallel
sam deploy --guided
# Stack name:          device-registry-dev
# AWS Region:          eu-central-1
# Parameter overrides: Environment=dev
# Confirm changes:     Y
# Allow SAM to create roles: Y
```

### Subsequent deployments

```bash
sam build --parallel --cached && sam deploy
```

Or trigger GitHub Actions via the **Actions** tab.

---

## Cleanup

```bash
sam delete --stack-name device-registry-dev --region eu-central-1
```

> The DynamoDB table has `DeletionPolicy: Retain` — it survives stack deletion.
> Delete it manually in the console if you no longer need the data.

---

## Repository Structure

```
.
├── .github/workflows/deploy.yml    CI/CD pipeline
├── docs/
│   ├── architecture.md             Detailed diagrams and design decisions
│   ├── oidc-setup.md               One-time AWS IAM + OIDC configuration
│   ├── evidence/                   Deployment screenshots (post-deploy)
│   └── postman/                    Importable Postman collection
├── scripts/
│   ├── verify.py                   Structural health checks (51 assertions)
│   └── deployment_check.py         Pre-deploy readiness verification
├── src/
│   ├── handlers/                   One Lambda handler per endpoint
│   ├── models/                     Device dataclass + DynamoDB serialisation
│   ├── repositories/               DynamoDB operations (create/get/list/update/delete)
│   ├── validation/                 Input validation for create and update
│   └── utils/                      Shared logging config + HTTP response helpers
├── tests/
│   ├── unit/                       59 tests, moto-mocked DynamoDB
│   └── integration/                Live API tests (requires deployed stack)
├── template.yaml                   AWS SAM infrastructure definition
├── samconfig.toml                  SAM CLI defaults (region, stack name)
├── pytest.ini                      Test runner configuration
└── requirements*.txt               Runtime and dev dependencies
```

---

## Future Improvements

In priority order:

1. **API authentication** — the HTTP API is currently open. Add an IAM authorizer
   (`AuthorizationType: AWS_IAM`) for service-to-service callers, or a Lambda authorizer
   validating an API key / JWT for external clients. Required before any public exposure.
2. **Pagination on `GET /devices`** — `limit` + `nextToken` query params backed by
   DynamoDB `Limit` + `ExclusiveStartKey`. Most important functional gap.
3. **GSI for type/status filtering** — `GET /devices?type=sensor` with a GSI Query
   instead of Scan. Eliminates full-table reads for filtered results.
4. **Structured JSON logging** — [`aws-lambda-powertools`](https://docs.powertools.aws.dev/lambda/python/)
   for CloudWatch Logs Insights-compatible output.
5. **OpenAPI spec** — attach to API Gateway for auto-generated docs and client SDKs.
6. **Dead-letter queues** — if the API grows to include async/event-driven patterns.

---

## License

Released under the [MIT License](LICENSE).
