# 0005 — Single GSI keyed on type + createdAt

## Context

`GET /devices` originally ran a full-table Scan. Scans read every item and are
billed for every item, so cost and latency grow with table size regardless of how
many items match. The common filter in practice is by device type.

The options were: one GSI per filterable attribute; a single GSI with a composite
partition key such as `type#status`; or one GSI on the attribute that matters
most.

## Decision

One global secondary index, `type-createdAt-index`, partitioned on `type` with
`createdAt` as the sort key, projecting all attributes.

## Consequence

`GET /devices?type=sensor` becomes a Query. It reads only matching items, returns
them newest-last by `createdAt` without a sort step, and pages natively through
the same `ExclusiveStartKey` mechanism as the base table. Cost scales with the
result set instead of the table.

Unfiltered `GET /devices` is still a Scan, bounded per request by `limit`. That is
deliberate: there is no partition key that means "everything", and inventing one —
a constant attribute every item shares — would put the whole table in one
partition and create a hot key. A bounded Scan is the honest answer for a listing
that has no filter.

The sharp edge is combined filters. `?type=sensor&status=active` cannot be served
by this index: `status` is not part of its key, so it would have to be applied as
a filter expression *after* the Query reads the items. Filter expressions run
after the read is billed, so the cost is the same as reading every sensor and
discarding some. With four types and three statuses the cardinality is tiny, so
today it does not matter. If status filtering became a primary access pattern, the
fix is a second GSI with a composite `type#status` partition key — which then
needs that attribute written and maintained on every update, which is precisely
the trade being deferred.

The `ALL` projection means the index stores a full copy of every item, roughly
doubling storage. At this size that is cheaper than the alternative — a
`KEYS_ONLY` projection would make every list a Query followed by N GetItems.
