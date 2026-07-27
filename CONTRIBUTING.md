# Contributing

Thanks for taking a look. This is a portfolio project maintained by
[@Joun-Mikhail](https://github.com/Joun-Mikhail), but issues and pull requests
are welcome.

## Getting set up

No AWS account is needed to work on this repository. The tests run against a
`moto`-mocked DynamoDB.

```bash
git clone https://github.com/Joun-Mikhail/device-registry-serverless-api.git
cd device-registry-serverless-api

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
pre-commit install
```

## The checks CI runs

Run these before pushing — they are exactly what CI enforces, so a clean local
run means a green pull request.

```bash
pytest tests/unit/ --cov=src --cov-fail-under=80   # unit tests + coverage gate
pytest tests/contract --no-cov                     # responses match openapi.yaml
ruff check .                                       # lint
python scripts/verify.py                           # structural health checks
```

`pre-commit run --all-files` runs the lint, whitespace, and secret-scan hooks on
demand.

A few things worth knowing:

- **Coverage must stay at or above 80%.** CI fails the build below that.
- **`ruff` runs with its default rule set**, pinned to the version in
  `requirements-dev.txt`. Suppress a rule with a per-line `# noqa: RULE` and a
  comment explaining why, rather than adding a repository-wide ignore — a blanket
  ignore silently disables the rule for future code too.
- **`detect-secrets` runs against a committed baseline.** If it flags something
  you know is not a secret, re-audit the baseline rather than deleting the
  finding: `detect-secrets scan --baseline .secrets.baseline`.

## Layout

Requests flow through four layers, and changes are easiest to review when they
stay in the layer they belong to:

| Layer | Location | Responsibility |
|---|---|---|
| Handler | `src/handlers/` | Parse the event, call down, shape the response |
| Validation | `src/validation/` | Type, length, and enum checks before any I/O |
| Repository | `src/repositories/` | DynamoDB operations |
| Model | `src/models/` | The `Device` dataclass and its serialisation |

Handlers return responses only through the helpers in `src/utils/response.py`
(`success`, `error`, `not_found`, `conflict`, `internal_error`) so the error
envelope stays consistent across every endpoint.

## Tests

- Name tests for the behaviour they pin down, not the function they call —
  `test_returns_400_when_path_parameters_is_null` rather than `test_get_device_2`.
- A bug fix should come with a test that fails without the fix. If the test
  passes against the unfixed code, it is not testing the bug.
- The contract suite asserts that handler responses conform to `docs/openapi.yaml`.
  If you change a response shape, update the spec in the same commit.

## Commits and pull requests

- Keep commits small and focused; one logical change each.
- Write the commit body to explain *why*, not to restate the diff.
- Fill in the pull request template. If a section does not apply, say so rather
  than deleting it.
- CI must be green before merge.

## Deployment

Deployment is manual and not part of the pull request flow. The `deploy` job is
gated on `workflow_dispatch`, so merging never deploys anything. See
[`docs/oidc-setup.md`](docs/oidc-setup.md) for the one-time IAM and OIDC setup
that job depends on.
