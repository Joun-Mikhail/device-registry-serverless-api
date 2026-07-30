# Interview notes — personal preparation

> **This file is preparation material, not project documentation.** It is the
> hardest questions a senior engineer could ask about this codebase, with answers
> grounded in what the code actually does. If you would rather it were not public,
> add `docs/interview-notes.md` to `.gitignore` and remove it from the index with
> `git rm --cached`.
>
> Numbers here are only stated where they were measured. Anything marked
> `TODO(verify)` has not been, and should not be quoted until it is.

---

### 1. Why five Lambda functions instead of one with a router?

Each route gets its own IAM role, so the read paths physically cannot write — a
shared function would need the union of every permission, which is full CRUD.
Failures isolate: a bad update deploy leaves reads working. Logs separate by route
for free, because the log group *is* the route.

The cost is real: five cold-start profiles instead of one warm function, and the
shared `utils`/`models`/`repositories` code is packaged into all five artifacts.
Past roughly a dozen routes I would switch to one function with an internal
router, keeping the same layering. See ADR-0001.

### 2. What breaks first at 10 million devices?

Unfiltered `GET /devices`. It is still a Scan — bounded per request by `limit`, so
one request is fine, but paging the whole table means reading all 10M items and
paying for all of them. At that size a full listing stops being a sensible
operation at all.

Second: the `ALL` projection on the GSI means the index holds a full copy of every
item, so storage roughly doubles.

Third, less obvious: `deviceId` is a UUIDv4 partition key, which distributes
beautifully — that part scales fine. The `type` GSI does not: four device types
means four partitions, so a large registry concentrates writes on a handful of
keys and can hit the per-partition throughput ceiling. The fix is a sharded key
(`type#0..N`) with scatter-gather reads.

### 3. Why is the unfiltered list still a Scan? Isn't that the thing you fixed?

I fixed the filtered path. The unfiltered one is deliberately still a Scan because
there is no partition key meaning "everything". Inventing a constant attribute so
every item shares one key would put the entire table in a single partition and
create a hot key — worse than the Scan. A bounded Scan is the honest answer for a
listing with no filter. ADR-0005.

### 4. Your pagination token is base64, not signed. Is that a vulnerability?

Not today, and I can say exactly why. It is encoded for opacity, not secrecy —
anyone can decode it and see a `deviceId`, and anyone can craft one to start from
an arbitrary key. Neither grants anything, because the API is single-tenant behind
one shared key: a caller who can page can already read everything.

It becomes a real vulnerability the moment items are scoped per tenant, because a
crafted token would read across that boundary. At that point it needs an HMAC over
the key plus caller identity, verified on decode. ADR-0006.

### 5. Why does your delete function have permission to read?

Because `DynamoDBCrudPolicy` is the narrowest SAM policy template that covers a
conditional delete — SAM ships no "DeleteItem only" template. Update has the same
problem. It is broader than least privilege and I know it.

Closing it means dropping the SAM template for an inline policy listing
`dynamodb:DeleteItem` against the table ARN. Small change, right thing before
production. Left as-is because the policy templates keep the template readable,
and this is a conscious trade rather than something I missed. ADR-0008.

### 6. `to_response()` just calls `to_item()` — so your database schema is your public API contract?

Yes, and that is the weakest part of the design. Renaming a stored attribute
silently changes the API. The layering is otherwise clean, and this is the one
place it leaks.

The fix is to make `to_response()` an explicit field mapping so the two shapes can
diverge. I have not done it because nothing has needed them to diverge yet, and
inventing a mapping layer before there is a second shape is speculative — but it
is the first thing I would change if this had a real consumer. ADR-0004.

### 7. Why an API key rather than Cognito?

Because this is machine-to-machine. Devices do not sign up interactively, have no
email addresses, and do not refresh OAuth tokens. API keys — or mTLS at higher
assurance — are the right pattern for a device plane. Cognito is right for a
human-facing console, which this does not have.

Two triggers would flip it: a web console with real users, or per-device ownership
scoping. Both need per-caller identity in the request, which is a JWT with claims,
not a shared secret. ADR-0007.

### 8. Two clients PATCH the same device at once. What happens?

No lost update, because there is no read-modify-write. `update()` issues a single
DynamoDB `UpdateItem` with a `SET` of only the supplied attributes and a
`ConditionExpression` of `attribute_exists(deviceId)`. Concurrent PATCHes to
*different* fields both apply. Concurrent PATCHes to the *same* field are
last-writer-wins at the item level.

What is missing is optimistic concurrency: there is no version attribute, so a
client cannot say "update only if you still have the version I read". If
conflicting writes needed detection rather than silent resolution, I would add a
`version` attribute and a `ConditionExpression` on it, returning 409 on mismatch.

### 9. Coverage is 91.9%. What is the missing 8%?

Mostly the boundary `except Exception` blocks in each handler — the paths that
convert an unexpected failure into a 500. They are hard to reach without injecting
a fault into boto3, and testing them proves the framework works rather than that
my logic does.

The parts I care about are covered: validation is 92%, the model 100%, pagination
100%, logging 100%, the authorizer 97%. The floor in CI is 91, which is the
measured value rounded down — so deleting real coverage fails the build rather
than silently passing.

### 10. Why is there no idempotency key on POST?

There is not one, and a client that retries a create after a timeout gets two
devices with different UUIDs. That is a genuine gap for a device registry, where
provisioning retries are normal.

The fix is a caller-supplied `Idempotency-Key` header, stored as a conditional
write against a dedupe table or attribute with a TTL, returning the original
response on replay. `aws-lambda-powertools` has an idempotency utility that does
exactly this. I would prioritise it above almost anything else remaining.

### 11. What is your cold start latency? What is p99?

`TODO(verify)` — not measured, and I will not quote a number I have not seen. The
functions are 128 MB Python 3.12 with boto3 from the runtime and no Lambda layer,
which is the light end of the spectrum, but that is a reason to expect it to be
good rather than evidence that it is.

Measuring it needs a deployed stack; X-Ray tracing and a p99 duration alarm are
the planned next phase.

### 12. What happens to a request that fails repeatedly? Any DLQ?

No dead-letter queue, and for this architecture that is correct rather than an
omission: these are synchronous API Gateway invocations. A DLQ applies to
asynchronous invocation, where there is no caller to return an error to. Here a
failure returns a 500 to the client, which decides whether to retry.

A DLQ becomes necessary the moment anything async appears — an SQS-triggered
ingestion path or an EventBridge consumer. That is listed under Future
Improvements for exactly that reason.

### 13. Why moto rather than LocalStack or real integration tests?

moto runs in-process, so the whole unit suite finishes in about nine seconds with
no Docker and no AWS account — which is why CI is cheap and a contributor can
clone and run tests immediately.

The honest limitation: moto is a reimplementation, not DynamoDB. It can accept
things real DynamoDB rejects, so a passing suite is not proof the query is valid.
That is why `tests/integration/` exists to run against a real deployed stack, and
why those tests skip unless `API_BASE_URL` is set rather than pretending to pass.

### 14. What did you deliberately not build, and why?

- **Per-caller credentials** — shared key is right for M2M until tenancy exists.
- **Optimistic locking** — no conflicting-write problem has appeared yet.
- **Idempotency** — the one on this list I actually regret; see Q10.
- **A DLQ** — meaningless for synchronous invocations.
- **Multi-region / DynamoDB global tables** — a portfolio project does not need
  five-nines, and it would multiply cost for no demonstrated requirement.
- **A second GSI for `status`** — four types and three statuses is tiny
  cardinality, so a filter expression is cheaper than the write amplification a
  composite-key GSI would add on every update.
- **CDK** — the template is meant to be read; a program has to be executed in your
  head first. ADR-0002.

### 15. How do you know the OpenAPI spec matches the code?

Contract tests — 13 of them. They exercise the real handlers against a mocked
DynamoDB and assert each response validates against the schema in
`docs/openapi.yaml`. If a response shape drifts from the spec, the suite fails and
names the offending field.

That covers response shapes. It does *not* cover everything: the spec's
descriptions, examples and the auth scheme are not machine-verified against
behaviour. Property-based testing with schemathesis would close more of that gap.

---

## Questions I would struggle with

Worth knowing where the thin ice is:

- **"Walk me through a production incident on this system."** There has not been
  one. Nothing has been deployed under real traffic, so any answer is a
  hypothetical and it would be better to say so than to invent a war story.
- **"What is this costing you a month?"** `TODO(verify)` — inside free tier by
  design, but not measured against a real bill.
- **"Show me the dashboard."** Does not exist yet. Observability is the next
  phase; today there is structured JSON logging with request-ID correlation and
  nothing aggregating it.
