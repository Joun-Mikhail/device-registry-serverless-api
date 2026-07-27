---
name: Bug report
about: Something behaves differently from what the README or OpenAPI spec describes
title: ''
labels: bug
assignees: Joun-Mikhail
---

## What happened

<!-- The actual behaviour, including the response body and status code. -->

## What you expected

<!-- Quote the README or docs/openapi.yaml if it documents the expected behaviour. -->

## How to reproduce

<!-- A failing test is the most useful form. Otherwise, the request that triggers it. -->

```bash
curl -X GET "https://<api-url>/dev/devices/..." -i
```

## Environment

- Ran against: <!-- local moto tests / deployed dev stack -->
- Python version:
- Commit or branch:

## Anything else

<!-- Logs, tracebacks, or the CloudWatch requestId if you have one. -->
