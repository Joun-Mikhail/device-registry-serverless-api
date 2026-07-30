# Observability

What exists today, what it is for, and the queries worth keeping.

Every handler is wrapped by `log_invocation` ([`src/utils/logging.py`](../src/utils/logging.py)),
which emits exactly one JSON line per request:

```json
{
  "timestamp": "2026-07-27T08:04:34.659209+00:00",
  "level": "INFO",
  "logger": "handlers.create_device",
  "message": "request",
  "operation": "CreateDevice",
  "requestId": "8f3a...",
  "method": "POST",
  "path": "/devices",
  "status": 201,
  "latencyMs": 21.64,
  "userAgent": "PostmanRuntime/7.x"
}
```

One line per request, with the fields as top-level keys, is what makes the queries
below possible. Logs Insights parses JSON automatically, so `status` and
`latencyMs` are queryable fields rather than substrings to regex out of a message.

Unhandled exceptions are logged at `ERROR` with `status: 500` and a serialised
traceback in `exc_info`. The traceback goes to the log and never to the caller.

---

## Saved Logs Insights queries

Run these from **CloudWatch → Logs Insights**, selecting the
`/aws/lambda/device-registry-*` log groups. Each is written against the fields
above, so they work against the logging that exists today.

### 1. Everything that happened during one request

The first query to run when someone reports a problem and gives you a request ID.
Because `requestId` is on every line, this reconstructs the whole request across
whichever function handled it.

```
fields @timestamp, operation, method, path, status, latencyMs, level
| filter requestId = "REPLACE-WITH-REQUEST-ID"
| sort @timestamp asc
```

### 2. Error rate by route, last hour

Answers "is it broken, and is it broken everywhere or in one place". Splitting
`errors` from `total` in the same row means you read a rate rather than eyeballing
two charts.

```
fields operation, status
| filter @timestamp > ago(1h)
| stats count(*) as total,
        sum(status >= 500) as errors,
        sum(status >= 500) * 100.0 / count(*) as errorPct
  by operation
| sort errorPct desc
```

### 3. Latency percentiles by route

`avg` hides the problem: a route can average 40 ms while its p99 sits near the
10-second timeout. This is the query that tells you which route to look at, and
`max` next to `p99` shows whether the tail is one outlier or a pattern.

```
fields operation, latencyMs
| filter ispresent(latencyMs) and @timestamp > ago(3h)
| stats count(*) as calls,
        pct(latencyMs, 50) as p50,
        pct(latencyMs, 95) as p95,
        pct(latencyMs, 99) as p99,
        max(latencyMs) as worst
  by operation
| sort p99 desc
```

### 4. What callers are getting rejected for

Validation failures are not errors — they are the API working. But a spike in one
message usually means a client integrated against a misread contract, and this
surfaces which one.

```
fields @message
| filter status = 400
| parse @message '"message":"*"' as reason
| stats count(*) as hits by reason
| sort hits desc
| limit 20
```

### 5. Authentication failures

The authorizer logs a denial without ever logging the key
([ADR-0007](decisions/0007-api-key-over-cognito.md)). A steady trickle is normal —
scanners find every public endpoint. A sharp spike from a low baseline is worth
attention.

```
fields @timestamp, @message
| filter @logStream like /authorizer/ and @message like /denied/
| stats count(*) as denials by bin(5m)
| sort @timestamp desc
```

---

## Alarms

Defined in [`template.yaml`](../template.yaml), all publishing to one SNS topic.

| Alarm | Fires when | Why that threshold |
|---|---|---|
| `lambda-errors` | ≥1 error in 5 minutes | For a service with this traffic, one unhandled error is a real event, not noise. Handled 4xx responses are not errors and do not count. |
| `lambda-p99-duration` | p99 > 3000 ms for 2 periods | The function timeout is 10 s. A p99 within a factor of three of timing out means the tail is heading for failure. Two periods, so a single spike does not page. |
| `dynamodb-throttles` | ≥1 throttled request | `PAY_PER_REQUEST` still throttles: on-demand capacity ramps, so a sharp spike can be rejected before the table scales. |

All three use `TreatMissingData: notBreaching`. On a low-traffic service, no data
means nobody called the API — alarming on silence would page constantly.

**The email address is a stack parameter defaulting to empty**, so the template
carries no personal address and deploys for anyone. Supply it at deploy time:

```bash
sam deploy --parameter-overrides AlarmEmail=you@example.com
```

With no address the alarms still evaluate and still show state in the console;
they simply have nowhere to send mail. AWS sends a confirmation email that has to
be accepted before the subscription becomes active.

---

## Dashboard

`AWS::CloudWatch::Dashboard` named `device-registry-<env>`, so it is created and
versioned with the stack rather than clicked together in the console. The
`DashboardUrl` stack output links straight to it.

| Widget | Reads |
|---|---|
| Invocations by route | Which endpoints are actually used |
| Errors by route | Stacked, so one failing route is visible against the rest |
| Duration p50 / p99 | With the alarm threshold and the 10 s timeout drawn as annotations, so the headroom is visible rather than inferred |
| DynamoDB capacity and throttles | Read and write units with throttles overlaid in red |
| Recent failures | A live Logs Insights table of `status >= 500` across all five log groups |

---

## What is not here yet

Named plainly, because a reviewer will ask.

- **No distributed tracing.** X-Ray is not enabled, so there is no service map and
  no per-segment timing inside a request. `requestId` correlation covers "what
  happened", not "where the time went".
- **No custom business metrics.** Devices created, validation failures and
  not-found counts are visible in logs but are not EMF metrics, so they cannot be
  alarmed on or charted without a Logs Insights query.
- **No measured baseline.** Cold start, p50 and p99 are unknown — the alarm
  thresholds above are reasoned from the 10 s timeout, not derived from observed
  traffic. Once the stack has run under load they should be re-set from the real
  distribution rather than from first principles.

Closing the first two is `aws-lambda-powertools`: `Tracer` for X-Ray and `Metrics`
for EMF. That is the remainder of this phase.
