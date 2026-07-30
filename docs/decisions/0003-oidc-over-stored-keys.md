# 0003 — GitHub OIDC over stored AWS keys

## Context

The deploy workflow needs AWS credentials. The straightforward approach is an IAM
user with an access key pair stored as GitHub secrets.

## Decision

GitHub OIDC federation. The workflow requests a short-lived OIDC token
(`permissions: id-token: write`) and exchanges it for temporary credentials via
`aws-actions/configure-aws-credentials`, assuming a role whose trust policy is
scoped to this repository. The only stored secret is the role ARN, which is not
itself a credential.

## Consequence

There is no long-lived AWS key anywhere — not in the repository, not in GitHub
secrets, not on a laptop. A key that does not exist cannot leak, cannot be
committed by accident, and does not need a rotation policy. The credentials the
workflow receives expire in minutes and are scoped to one role.

The trust policy is the security boundary, and it has to be written carefully: a
subject condition of `repo:owner/name:*` would let *any* branch or pull request in
the repository assume the deploy role, including a branch pushed by a fork. The
condition needs to pin the ref.

The cost is setup friction. This cannot be configured from the repository — it
needs an IAM role and an OIDC identity provider created in the AWS account first,
which is a genuine barrier for anyone cloning this to try it. That one-time setup
is documented in [`docs/oidc-setup.md`](../oidc-setup.md).
