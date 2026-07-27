# Serverless Device Registry API

[![CI](https://github.com/Joun-Mikhail/device-registry-serverless-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Joun-Mikhail/device-registry-serverless-api/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://github.com/Joun-Mikhail/device-registry-serverless-api/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> A REST API for registering and managing IoT devices, built as a portfolio project
> to practise serverless patterns end to end.
> Built with Python, AWS Lambda, API Gateway HTTP API, and DynamoDB,
> packaged with AWS SAM and exercised by a GitHub Actions pipeline.

**Status —** Portfolio project, actively maintained as a learning exercise.

- **Runs on every push:** unit tests, contract tests, `ruff` lint, and secret
  scanning via GitHub Actions. These are the checks the badges above reflect.
- **Deployment:** the SAM stack (`template.yaml`) targets a single `dev`
  environment in `eu-central-1` and is deployed **manually** via
  *Actions → Deploy → Run workflow* using GitHub OIDC. **No public endpoint is
  published in this repository**, so there is no live URL to try.
- **Out of scope:** API authentication (the HTTP API has no authorizer), a
  multi-environment promotion pipeline, custom domains, autoscaling and cost
  tuning, and production-grade alerting. See
  [Future Improvements](#future-improvements) for the intended order of work.

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
| Observability | Structured JSON logging with request ID correlation; log groups declared with 7-day retention |

---

## Architecture

```mermaid
flowchart TB
    Client["Client<br/><i>Postman · curl · application</i>"]

    subgraph AWS["AWS · eu-central-1"]
        APIGW["API Gateway HTTP API"]

        subgraph Lambdas["Lambda · Python 3.12 · 128 MB · 10s"]
            direction TB
            Create["CreateDeviceFunction"]
            Read["GetDeviceFunction<br/>ListDevicesFunction"]
            Write["UpdateDeviceFunction"]
            Delete["DeleteDeviceFunction"]
        end

        DDB[("DynamoDB<br/>device-registry-dev<br/><i>PAY_PER_REQUEST</i>")]
        Logs[/"CloudWatch Logs<br/><i>7-day retention</i>"/]
    end

    Client -->|"HTTPS"| APIGW
    APIGW -->|"POST /devices"| Create
    APIGW -->|"GET /devices<br/>GET /devices/{deviceId}"| Read
    APIGW -->|"PATCH /devices/{deviceId}"| Write
    APIGW -->|"DELETE /devices/{deviceId}"| Delete

    Create -->|"PutItem<br/><i>conditional</i>"| DDB
    Read -->|"GetItem · Query · Scan"| DDB
    Write -->|"UpdateItem"| DDB
    Delete -->|"DeleteItem<br/><i>conditional</i>"| DDB

    Lambdas -.->|"structured JSON"| Logs

    classDef edge fill:#e8f0fe,stroke:#4285f4,color:#1a1a1a
    classDef store fill:#fce8e6,stroke:#ea4335,color:#1a1a1a
    classDef obs fill:#fef7e0,stroke:#f9ab00,color:#1a1a1a
    class Client,APIGW edge
    class DDB store
    class Logs obs
```

Each request flows through four layers before reaching DynamoDB:

```mermaid
flowchart LR
    A["handler<br/><i>parse event</i>"] --> B["validation<br/><i>type · length · enum</i>"]
    B --> C["repository<br/><i>DynamoDB ops</i>"]
    C --> D["model<br/><i>Device dataclass</i>"]
    B -.->|"invalid"| E["400<br/>VALIDATION_ERROR"]
    C -.->|"conflict"| F["409<br/>CONFLICT"]
    C -.->|"missing"| G["404<br/>NOT_FOUND"]
    C -.->|"unexpected"| H["500<br/>INTERNAL_ERROR"]

    classDef ok fill:#e6f4ea,stroke:#34a853,color:#1a1a1a
    classDef err fill:#fce8e6,stroke:#ea4335,color:#1a1a1a
    class A,B,C,D ok
    class E,F,G,H err
```

The ASCII rendering of these diagrams is kept in
[`docs/architecture.md`](docs/architecture.md), alongside the request lifecycle,
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

Expected output: `99 passed, coverage 91%`.

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
{ "error": { "code": "VALIDATION_ERROR", "message": "'type' must be one of: ['actuator', 'controller', 'gateway', 'sensor']." } }
```

**409 Conflict** is returned if a device with the same ID already exists.

---

### Get a device — `GET /devices/{deviceId}`

```bash
curl https://<api-url>/dev/devices/a3f1c2d4-8b5e-4f9a-bc12-d3e4f5a6b7c8
```

**200 OK** (device object) or **404 Not Found:**
```json
{ "error": { "code": "NOT_FOUND", "message": "Device not found." } }
```

---

### List devices — `GET /devices`

Supports cursor pagination and filtering by type.

| Query param | Default | Notes |
|---|---|---|
| `limit` | 25 | 1–100 items per page |
| `nextToken` | — | Opaque cursor from a previous response |
| `type` | — | `sensor` \| `actuator` \| `gateway` \| `controller` — served by the GSI |

```bash
# First page of 25
curl "https://<api-url>/dev/devices"

# Page of 10, filtered by type (uses the type-createdAt GSI Query)
curl "https://<api-url>/dev/devices?type=sensor&limit=10"

# Next page
curl "https://<api-url>/dev/devices?limit=10&nextToken=<token-from-previous-response>"
```

**200 OK:**
```json
{ "items": [ { ... } ], "count": 10, "nextToken": "eyJkZXZpY2VJZCI6..." }
```

`nextToken` is present only when more results exist.

> Filtering by `type` runs an efficient GSI **Query**. The unfiltered list is a
> **paginated Scan** (bounded by `limit` per request) — the one remaining
> full-table operation, documented in [Architecture](docs/architecture.md).

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
├── unit/                            99 tests
│   ├── test_device_model.py         Dataclass serialisation (6 tests)
│   ├── test_device_validator.py     Validation — create, update, list params (30 tests)
│   ├── test_device_repository.py    DynamoDB ops, GSI query, pagination, conflict (19 tests)
│   ├── test_handlers.py             End-to-end handler logic, mocked DB (34 tests)
│   ├── test_pagination.py           Opaque cursor encode/decode (6 tests)
│   └── test_logging.py              Structured JSON log shape + decorator (4 tests)
├── contract/                        13 tests
│   ├── test_openapi_valid.py        OpenAPI 3.0 spec is valid (2 tests)
│   └── test_contract.py             Every handler response conforms to the spec (11 tests)
└── integration/
    └── test_api.py                  Live API tests — skip if API_BASE_URL unset
```

**Run unit tests:**
```bash
pytest                              # uses pytest.ini defaults (tests/unit)
pytest tests/unit/ -v               # verbose
pytest --cov=src --cov-report=html  # HTML coverage report
```

**Running contract tests locally:**

Contract tests validate `docs/openapi.yaml` and assert that every handler response
conforms to its published response schema. They run against a `moto`-mocked
DynamoDB (no AWS account, no server needed).

```bash
pip install -r requirements-dev.txt
pytest tests/contract --no-cov -v
```

`--no-cov` is used because the contract suite is scoped to schema conformance, not
line coverage (the unit suite owns the 80% coverage gate). If a response ever drifts
from the spec, the contract test fails and prints the offending field and payload.

**Run integration tests:**
```bash
export API_BASE_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
pytest tests/integration/ -v
```

**Postman collection:** [`docs/postman/device-registry.postman_collection.json`](docs/postman/device-registry.postman_collection.json)

Import into Postman, set `base_url`, run in order. Each request includes automated
test assertions (status codes + response shape).

---

## Code Quality & Pre-commit

Local hooks (lint, whitespace, secret scan) are configured in
[`.pre-commit-config.yaml`](.pre-commit-config.yaml):

```bash
pip install -r requirements-dev.txt
pre-commit install          # run hooks automatically on every commit
pre-commit run --all-files  # or run them on demand
```

Hooks: `ruff` (lint, config in [`ruff.toml`](ruff.toml)), trailing-whitespace /
end-of-file fixers, `check-yaml` (`--unsafe`, for CloudFormation tags), and
[`detect-secrets`](https://github.com/Yelp/detect-secrets) against a committed
[`.secrets.baseline`](.secrets.baseline).

**Secret scanning:** `detect-secrets` blocks new credentials from being committed.
The baseline records reviewed, non-secret matches (the `"testing"` AWS stubs in
test fixtures and the regex patterns in `scripts/verify.py`). To re-audit:

```bash
detect-secrets scan --baseline .secrets.baseline   # refresh
detect-secrets audit .secrets.baseline             # review interactively
```

CI enforces the same `ruff` lint and `detect-secrets` scan on every push and PR
(the **Lint & Secret Scan** job), run directly so it doesn't depend on each
developer's pre-commit setup.

---

## CI/CD Pipeline

Two workflows. **`ci.yml`** (named *CI*, the badge above) runs the unit tests and
the coverage gate on every push and pull request. **`deploy.yml`** adds contract
tests and secret scanning, and holds the deploy job — which is gated on
`workflow_dispatch`, so it never runs on a push.

```mermaid
flowchart TB
    Push(["push · pull_request<br/>on main"]) --> CI
    Push --> Deploy

    subgraph CI["ci.yml — CI"]
        direction TB
        U["Unit Tests<br/><i>pytest tests/unit</i><br/><b>coverage ≥ 80%</b>"]
        L["Lint<br/><i>ruff check .</i>"]
    end

    subgraph Deploy["deploy.yml — Deploy"]
        direction TB
        UT["Unit Tests"] --> CT["Contract Tests<br/><i>responses ↔ openapi.yaml</i>"]
        LS["Lint &amp; Secret Scan<br/><i>ruff · detect-secrets</i>"]
        CT --> Gate{"event ==<br/>workflow_dispatch?"}
        LS --> Gate
        Gate -->|no| Skip["skipped"]
        Gate -->|yes| BD["Build &amp; Deploy<br/><i>OIDC → AssumeRoleWithWebIdentity</i><br/><i>sam build → sam deploy</i>"]
    end

    BD --> Stack[("CloudFormation<br/>device-registry-dev")]

    classDef gate fill:#fef7e0,stroke:#f9ab00,color:#1a1a1a
    classDef manual fill:#e8f0fe,stroke:#4285f4,color:#1a1a1a
    classDef skip fill:#f1f3f4,stroke:#9aa0a6,color:#3c4043
    class Gate gate
    class BD,Stack manual
    class Skip skip
```

No AWS credentials are needed for anything except the deploy job, which uses
GitHub OIDC rather than stored keys.

**First-time setup:** see [`docs/oidc-setup.md`](docs/oidc-setup.md) for the IAM
role and GitHub secret configuration.

---

## Monitoring & Logging

`template.yaml` provisions one log group per function, each with 7-day
retention. They are created when the stack is deployed:

| CloudWatch Log Group (defined in `template.yaml`) | Retention |
|---|---|
| `/aws/lambda/device-registry-create-dev` | 7 days |
| `/aws/lambda/device-registry-get-dev` | 7 days |
| `/aws/lambda/device-registry-list-dev` | 7 days |
| `/aws/lambda/device-registry-update-dev` | 7 days |
| `/aws/lambda/device-registry-delete-dev` | 7 days |

**Structured JSON logs.** Every handler is wrapped by the `log_invocation`
decorator ([`src/utils/logging.py`](src/utils/logging.py)), which emits one JSON
line per request so that, once deployed, CloudWatch Logs Insights can query by
field. Illustrative example of the shape the decorator produces (not a capture
from a deployed environment):

```json
{
  "timestamp": "2024-11-01T10:30:00.123456+00:00",
  "level": "INFO",
  "logger": "handlers.create_device",
  "message": "request",
  "operation": "CreateDevice",
  "requestId": "8f3a...",
  "method": "POST",
  "path": "/devices",
  "status": 201,
  "latencyMs": 12.4,
  "userAgent": "PostmanRuntime/7.x"
}
```

`requestId` is emitted to support cross-log correlation. Log verbosity is controlled by the
`LOG_LEVEL` environment variable in `template.yaml` — set to `DEBUG` without a
code change. Unhandled exceptions are logged at `ERROR` with `status: 500` and a
serialized traceback (never returned to the caller).

---

## Security

| Control | Implementation |
|---|---|
| No stored AWS keys | GitHub OIDC federation (`AssumeRoleWithWebIdentity`) |
| Least-privilege IAM | Per-function DynamoDB policy (Write / Read / Crud only) |
| Input validation | Type, length, and enum checks before any DB operation |
| Error isolation | Stack traces sent to the logger, never returned to callers |
| Secrets in code | None — `DEVICES_TABLE` injected by SAM at deploy time |
| Log retention | Log groups declared with 7-day retention to bound the data exposure window |
| CORS | `Access-Control-Allow-Origin: *` — permissive by design for `dev`; restrict before any public exposure |
| **API authentication** | **None — `template.yaml` declares no authorizer, so a deployed stack would expose an open HTTP API.** See Future Improvements item 1 before deploying anywhere public. |

---

## Deployment

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) ≥ 1.100
- Python 3.12
- AWS credentials (for manual deploy), or an OIDC role set up per
  [`docs/oidc-setup.md`](docs/oidc-setup.md) and its ARN stored as the
  `AWS_DEPLOY_ROLE_ARN` secret (for CI)

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
├── .github/
│   ├── dependabot.yml              Weekly pip dependency updates
│   └── workflows/
│       ├── ci.yml                  CI pipeline (unit tests + coverage gate + lint)
│       └── deploy.yml              CD pipeline (contract tests + manual SAM deploy)
├── docs/
│   ├── architecture.md             Detailed diagrams and design decisions
│   ├── oidc-setup.md               One-time AWS IAM + OIDC configuration
│   ├── openapi.yaml                OpenAPI 3.0 contract
│   ├── evidence/                   Capture instructions for deploy screenshots
│   └── postman/                    Importable Postman collection
├── scripts/
│   ├── verify.py                   Structural health checks (template, workflow, imports)
│   └── deployment_check.py         Pre-deploy readiness verification
├── src/
│   ├── handlers/                   One Lambda handler per endpoint
│   ├── models/                     Device dataclass + DynamoDB serialisation
│   ├── repositories/               DynamoDB operations (create/get/list/update/delete)
│   ├── validation/                 Input validation (create, update, list params)
│   └── utils/                      JSON logging, HTTP responses, pagination cursor
├── tests/
│   ├── unit/                       99 tests, moto-mocked DynamoDB
│   ├── contract/                   13 tests, response ↔ OpenAPI conformance
│   └── integration/                10 tests, skipped unless API_BASE_URL is set
├── template.yaml                   AWS SAM infrastructure definition
├── samconfig.toml                  SAM CLI defaults (region, stack name)
├── pytest.ini                      Test runner configuration
├── ruff.toml                       Lint configuration
├── vercel.json                     Disables Vercel git deployments (not a Vercel app)
├── .pre-commit-config.yaml         Local lint / whitespace / secret-scan hooks
├── .secrets.baseline               Reviewed detect-secrets baseline
├── .gitignore                      Build, cache, venv, and credential exclusions
├── LICENSE                         MIT
└── requirements*.txt               Runtime and dev dependencies
```

---

## Future Improvements

**Done:** ✅ cursor pagination (`limit` + `nextToken`) · ✅ GSI Query for `?type=`
filtering · ✅ OpenAPI 3.0 contract + contract tests in CI · ✅ structured error model
· ✅ structured JSON request logging · ✅ ruff + detect-secrets pre-commit & CI.

In priority order:

1. **API authentication** — the template declares no authorizer. Add an IAM authorizer
   (`AuthorizationType: AWS_IAM`) for service-to-service callers, or a Lambda authorizer
   validating an API key / JWT for external clients. Required before any public exposure.
2. **Eliminate the unfiltered Scan** — materialised index for the no-filter list.
3. **Dead-letter queues** — if the API grows to include async/event-driven patterns.
4. **CloudWatch metrics & alarms** — error-rate / p95-latency alarms (needs a live stack).

---

## License

Released under the [MIT License](LICENSE).
