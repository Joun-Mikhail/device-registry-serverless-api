# Architecture decision records

Short notes on choices that were not obvious, in the format Context / Decision /
Consequence. They exist so the reasoning survives after the reasoning is
forgotten — including the options that were rejected and what would make me
revisit them.

| # | Decision | Status |
|---|---|---|
| [0001](0001-one-lambda-per-endpoint.md) | One Lambda function per endpoint | Accepted |
| [0002](0002-sam-over-cdk-and-terraform.md) | AWS SAM over CDK or Terraform | Accepted |
| [0003](0003-oidc-over-stored-keys.md) | GitHub OIDC over stored AWS keys | Accepted |
| [0004](0004-layered-architecture.md) | Layered handlers → validation → repository → model | Accepted |
| [0005](0005-gsi-key-design.md) | Single GSI keyed on type + createdAt | Accepted |
| [0006](0006-opaque-pagination-token.md) | Opaque base64 pagination token | Accepted |
| [0007](0007-api-key-over-cognito.md) | API key authorizer, not Cognito | Accepted |
| [0008](0008-per-function-iam.md) | Per-function IAM policies | Accepted, with a known gap |
| [0009](0009-browser-client-with-demo-backend.md) | A browser client that ships its own demo backend | Accepted |
