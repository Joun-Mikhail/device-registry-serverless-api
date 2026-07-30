# 0008 — Per-function IAM policies

## Context

Because each route is its own Lambda ([0001](0001-one-lambda-per-endpoint.md)),
each can carry its own execution role. The alternative is one shared role with the
union of every permission.

## Decision

Each function gets the narrowest SAM policy template that covers its route:

| Function | Policy |
|---|---|
| Create | `DynamoDBWritePolicy` |
| Get, List | `DynamoDBReadPolicy` |
| Update, Delete | `DynamoDBCrudPolicy` |
| Authorizer | `AWSSecretsManagerGetSecretValuePolicy`, scoped to one secret ARN |

## Consequence

A compromised read path cannot write. The create path cannot delete. The
authorizer can read exactly one secret and touch nothing else. This is only
possible because the functions are separate — a shared role would need the union,
which is `Crud` for everything.

The gap, stated plainly because a reviewer will find it: **update and delete use
`DynamoDBCrudPolicy`, which is broader than they need.** Crud grants read, write
*and* delete, so the update function can delete items and the delete function can
read them. SAM ships no narrower template for "UpdateItem only" or "DeleteItem
only", and both routes need a conditional expression that requires more than a
plain write.

Closing it means dropping the SAM policy template and writing an inline policy
listing `dynamodb:UpdateItem` and `dynamodb:DeleteItem` against the table ARN. That
is a small change and is the right thing to do before anything resembling
production. It is left as-is here because the SAM templates keep the infrastructure
readable, and readability is this repository's primary job — but it is a
conscious trade, not an oversight.
