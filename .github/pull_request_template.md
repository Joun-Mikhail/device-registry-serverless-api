## What this changes

<!-- What does this do, and why? Link an issue with "Closes #123" if there is one. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behaviour change)
- [ ] Documentation
- [ ] Infrastructure / CI

## How it was verified

<!-- Paste the actual output rather than asserting it passed. -->

```
pytest tests/unit/ --cov=src --cov-fail-under=80
pytest tests/contract --no-cov
ruff check .
```

## Checklist

- [ ] Tests cover the change, and a bug fix has a test that fails without it
- [ ] Coverage is still at or above 80%
- [ ] `ruff check .` is clean, with any new `# noqa` carrying a reason
- [ ] `docs/openapi.yaml` updated if a response shape changed
- [ ] README updated if behaviour, counts, or structure changed
- [ ] CHANGELOG.md updated under Unreleased

## Notes for the reviewer

<!-- Anything deliberately left out, opinionated, or worth a closer look. -->
