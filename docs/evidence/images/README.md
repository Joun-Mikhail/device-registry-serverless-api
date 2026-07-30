# Captured evidence

Real captures, not mock-ups. Regenerate them by running the commands below.

| Image | What it shows | How it was produced |
|---|---|---|
| `api-session.png` | A real request/response session against the API — a successful create, a filtered paginated list, a validation rejection, and a 404. | `python scripts/local_server.py --seed`, then the `curl` commands shown in the image. Output is reproduced verbatim. |
| `api-auth.png` | The API refusing a request with no key and one with a wrong key, then serving a request that presents the right key. | `python scripts/local_server.py --seed --api-key "demo-key-abc123"`, then the `curl` commands shown. |
| `coverage-report.png` | The per-file coverage report. | `pytest tests/unit/ --cov=src --cov-report=html` |

The API in `api-session.png` is running locally against an in-memory DynamoDB
(moto). The handler, validation, repository and model code exercised is exactly
the code that runs in Lambda; only the DynamoDB backend is simulated.
