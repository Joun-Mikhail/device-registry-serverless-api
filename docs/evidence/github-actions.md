# Evidence: GitHub Actions Deployment

## What to capture here

After triggering the deployment workflow, replace this file with screenshots
of the completed run.

---

## How to trigger

1. On GitHub, navigate to your repository.
2. Click the **Actions** tab.
3. In the left sidebar, click **Deploy — Device Registry API**.
4. Click **Run workflow** → select branch `main` → environment `dev` → **Run workflow**.

---

## Screenshots to take

### 1 — Workflow run summary (`github-actions-run-summary.png`)

After the run completes (green tick):

1. Click the completed workflow run.
2. Screenshot the top-level summary showing:
   - Workflow name: `Deploy — Device Registry API`
   - Status: ✅ Success
   - Both jobs: **Unit Tests** ✅ and **Build & Deploy (SAM)** ✅
   - Duration and timestamp

### 2 — Unit test job logs (`github-actions-tests.png`)

1. Click the **Unit Tests** job.
2. Expand the **Run unit tests** step.
3. Screenshot showing pytest output:
   - `59 passed`
   - `Total coverage: 87%`

### 3 — Deploy job OIDC step (`github-actions-oidc.png`)

1. Click the **Build & Deploy (SAM)** job.
2. Expand the **Configure AWS credentials via OIDC** step.
3. Screenshot showing `AssumedRole` success (no access keys visible).

### 4 — SAM deploy output (`github-actions-sam-deploy.png`)

1. Still in the deploy job.
2. Expand the **Deploy to AWS** step.
3. Screenshot showing the CloudFormation changeset summary and
   `Successfully created/updated stack - device-registry-dev`.

### 5 — Stack outputs (`github-actions-outputs.png`)

1. Expand the **Print API base URL** step.
2. Screenshot showing the table with `ApiBaseUrl`, `DevicesTableName`, `DevicesTableArn`.

---

## What the test output should look like

```
============================= test session starts ==============================
...
59 passed in 28.12s
Total coverage: 87.30%
Required test coverage of 80% reached.
```

## What the deploy output should look like

```
CloudFormation events from stack operations (refresh every 5.0 seconds)
---------------------------------------------------------------------------------------------------------------------------------
ResourceStatus          ResourceType                         LogicalResourceId
---------------------------------------------------------------------------------------------------------------------------------
UPDATE_IN_PROGRESS      AWS::CloudFormation::Stack           device-registry-dev
...
UPDATE_COMPLETE         AWS::CloudFormation::Stack           device-registry-dev
---------------------------------------------------------------------------------------------------------------------------------

Successfully created/updated stack - device-registry-dev in eu-central-1
```
