# Captured evidence

Real captures, not mock-ups. Regenerate them by running the commands below.

| Image | What it shows | How it was produced |
|---|---|---|
| `api-session.png` | A real request/response session against the API — a successful create, a filtered paginated list, a validation rejection, and a 404. | `python scripts/local_server.py --seed`, then the `curl` commands shown in the image. Output is reproduced verbatim. |
| `coverage-report.png` | The per-file coverage report. | `pytest tests/unit/ --cov=src --cov-report=html` |

The API in `api-session.png` is running locally against an in-memory DynamoDB
(moto). The handler, validation, repository and model code exercised is exactly
the code that runs in Lambda; only the DynamoDB backend is simulated.
