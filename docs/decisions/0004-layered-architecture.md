# 0004 — Layered handlers → validation → repository → model

## Context

Each handler could talk to DynamoDB directly. For five CRUD routes that would
work, and would be less code.

## Decision

Four layers with one direction of dependency:

    handler      parse the event, shape the HTTP response
    validation   type, length and enum checks — pure functions, no I/O
    repository   DynamoDB operations, the only place boto3 is imported for data
    model        the Device dataclass and its serialisation

## Consequence

The validation layer is pure, so it is tested without mocking anything — 30 of
the tests need no AWS simulation at all, and they run in milliseconds. The
repository is the only place that knows DynamoDB exists, so the item shape,
condition expressions and pagination keys are in one file rather than smeared
across five handlers.

The boundary is also what makes the handlers uniform: every one of them parses,
validates, calls down, and returns through the helpers in `utils/response.py`, so
the error envelope is identical across routes by construction rather than by
discipline.

The cost is indirection. Creating a device touches four files, and for a change
this small that is more navigation than a direct call would need. There is also a
leak worth naming: `Device.to_response()` currently returns `to_item()`, so the
DynamoDB item shape *is* the public API shape. Renaming a stored attribute would
silently change the contract. Splitting them is the obvious next refactor.
