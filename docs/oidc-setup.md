# GitHub OIDC → AWS Setup

The deployment pipeline uses GitHub's OIDC provider to authenticate to AWS — no
long-lived access keys are stored anywhere. This is a one-time setup per AWS account.

---

## Prerequisites

- AWS account with permissions to create IAM roles and OIDC identity providers
- AWS CLI installed and configured with admin credentials
- Your GitHub username and repository name

---

## Step 1 — Add GitHub as an OIDC Identity Provider

Run once per AWS account:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --region eu-central-1
```

If it already exists, skip this step.

---

## Step 2 — Create the IAM Deploy Role

The `GITHUB_ORG` and `REPO_NAME` below are already set for this repository. If you
fork it under a different account, change `GITHUB_ORG` to your GitHub username.

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
GITHUB_ORG="Joun-Mikhail"
REPO_NAME="device-registry-serverless-api"

# Create the trust policy document
cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${REPO_NAME}:*"
        }
      }
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name device-registry-github-deploy \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Assumed by GitHub Actions to deploy device-registry-serverless-api"
```

---

## Step 3 — Attach Permissions to the Role

The role needs permissions to deploy the SAM stack. Attach AWS managed policies:

```bash
# CloudFormation
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AWSCloudFormationFullAccess

# Lambda
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

# API Gateway
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator

# DynamoDB
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# IAM (to create Lambda execution roles)
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess

# S3 (for SAM deployment artefacts)
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# CloudWatch Logs
aws iam attach-role-policy \
  --role-name device-registry-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

> **Note:** For a personal portfolio project, the broad managed policies above are
> acceptable. In a team environment, replace with a least-privilege custom policy
> covering only the specific IAM actions SAM needs.

---

## Step 4 — Copy the Role ARN

```bash
aws iam get-role \
  --role-name device-registry-github-deploy \
  --query "Role.Arn" \
  --output text
```

Output:
```
arn:aws:iam::123456789012:role/device-registry-github-deploy
```

---

## Step 5 — Add the ARN to GitHub Secrets

1. Go to your GitHub repository.
2. Click **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret**.
4. Name: `AWS_DEPLOY_ROLE_ARN`
5. Value: the ARN from Step 4.
6. Click **Add secret**.

---

## Step 6 — Create the `dev` GitHub Environment

The workflow uses `environment: dev` which scopes the secret and can enforce
protection rules (e.g. required reviewers).

1. Go to **Settings** → **Environments**.
2. Click **New environment** → name it `dev`.
3. Optionally add yourself as a required reviewer.
4. Click **Configure environment**.

---

## Verify

Trigger the workflow:

1. Go to **Actions** → **Deploy — Device Registry API**.
2. Click **Run workflow** → `dev` → **Run workflow**.
3. The OIDC step should show `AssumedRole` success.
4. The deploy step should show `Successfully created/updated stack`.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Could not load credentials` | Role ARN wrong or secret missing | Re-check `AWS_DEPLOY_ROLE_ARN` secret |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | Trust policy condition mismatch | Verify `sub` condition matches your repo |
| `CAPABILITY_IAM required` | CloudFormation creating IAM roles | `--capabilities CAPABILITY_IAM` is already in the deploy command |
| `S3 bucket does not exist` | First deploy needs `--resolve-s3` | `resolve_s3 = true` is already in `samconfig.toml` |
