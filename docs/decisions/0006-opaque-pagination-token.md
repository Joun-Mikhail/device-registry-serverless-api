# 0006 — Opaque base64 pagination token

## Context

DynamoDB paginates by returning a `LastEvaluatedKey`, which the caller passes back
as `ExclusiveStartKey`. That key is a raw DynamoDB item-key structure. The API has
to expose *something* to let a client fetch the next page.

The options were to return the key as-is, to return a page number or offset, or to
encode the key into an opaque token.

## Decision

`nextToken`: the `LastEvaluatedKey` serialised to JSON with sorted keys, then
URL-safe base64. Absent from the response when there are no further pages. A token
that does not decode to a JSON object is rejected with 400, not 500.

## Consequence

Clients cannot build a dependency on the internal key structure, so the index or
key schema can change without breaking them — that is the whole point of making it
opaque. It is URL-safe, so it survives a query string without escaping. Its
absence is the end-of-results signal, which means a client loops until the field
is missing rather than comparing counts.

Offset pagination was rejected because DynamoDB has no offset. Emulating one means
reading and discarding every skipped item, so page 50 costs fifty pages of reads.

The honest limitation: the token is encoded, not encrypted and not signed. Anyone
can base64-decode it and see a `deviceId`, and anyone can craft one to start a scan
from an arbitrary key. Neither is a privilege escalation here — the API is
single-tenant behind one shared key, so a caller who can page can already read
everything. It *would* become one the moment items are scoped per tenant, because
a crafted token would be a way to read across that boundary. If per-caller scoping
arrives, the token needs an HMAC over the key plus the caller identity, verified
on decode.

Tokens also inherit DynamoDB's semantics: they are not snapshots. An item inserted
between two page requests can appear or be skipped. For a device registry that is
acceptable; for anything requiring a consistent view it would not be.
