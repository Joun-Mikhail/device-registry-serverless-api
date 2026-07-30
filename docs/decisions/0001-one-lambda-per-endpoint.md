# 0001 — One Lambda function per endpoint

## Context

Five routes: create, get, list, update, delete. They could be served by one
function that inspects the HTTP method and path, or by five functions with one
route each.

A single function is a smaller deployment, fewer cold starts in aggregate, and
one place to look. It is also how most small serverless projects start, and how
a framework like Flask-inside-Lambda would force it.

## Decision

Five functions, one per route, each with its own handler module, its own IAM
policy and its own log group.

## Consequence

Each function gets exactly the DynamoDB permissions its route needs — the read
routes cannot write, which a single shared function could not express (see
[0008](0008-per-function-iam.md)). Failures are isolated: a bad deploy of the
update path leaves reads working. Metrics and logs separate by route with no
extra instrumentation, because the log group *is* the route.

The costs are real. Five functions mean five cold-start profiles rather than one
warm function serving everything, so a low-traffic route stays cold longer. The
shared code in `utils/`, `models/` and `repositories/` is packaged into every
function, so the deployment artifact is duplicated five times. Adding a route
means touching `template.yaml`, not just adding a branch to a router.

At this scale the isolation is worth more than the duplication. If the route
count grew past roughly a dozen, or if cold starts became the dominant latency
cost, a single function with an internal router — still layered the same way —
would be the reasonable retreat.
