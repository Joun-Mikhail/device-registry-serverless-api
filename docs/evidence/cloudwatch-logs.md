# Evidence: CloudWatch Logs

## What to capture here

After sending at least one request to the API, replace this file with screenshots
of the CloudWatch log groups showing structured log output.

---

## Screenshots needed

### 1 — Log group list with retention (`cloudwatch-log-groups.png`)

1. Open [CloudWatch → Log groups](https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#logsV2:log-groups) in **eu-central-1**.
2. Filter by `/aws/lambda/device-registry`.
3. Screenshot the list showing all five groups with **7-day retention**:
   - `/aws/lambda/device-registry-create-dev`
   - `/aws/lambda/device-registry-get-dev`
   - `/aws/lambda/device-registry-list-dev`
   - `/aws/lambda/device-registry-update-dev`
   - `/aws/lambda/device-registry-delete-dev`

### 2 — Successful invocation log (`cloudwatch-create-success.png`)

1. Click `/aws/lambda/device-registry-create-dev`.
2. Click the most recent log stream.
3. Screenshot showing a log stream with:
   - `START RequestId: ...`
   - `[INFO] CreateDevice invoked request_id=<uuid>`
   - `END RequestId: ...`
   - `REPORT RequestId: ... Duration: ... Memory Size: 128 MB`

### 3 — 404 response log (`cloudwatch-get-404.png`)

Send a `GET /devices/00000000-0000-0000-0000-000000000000` request, then:

1. Open `/aws/lambda/device-registry-get-dev` log stream.
2. Screenshot showing the invocation log (no error, just a 404 returned correctly).

---

## Tail logs from the CLI

```bash
# Requires AWS SAM CLI
sam logs --stack-name device-registry-dev --name CreateDeviceFunction --tail

# Or with AWS CLI directly
aws logs tail /aws/lambda/device-registry-create-dev --follow --region eu-central-1
```

---

## Expected log format

```
START RequestId: abc-123 Version: $LATEST
[INFO]  2024-11-01T10:30:00.000Z  abc-123  CreateDevice invoked request_id=abc-123
END RequestId: abc-123
REPORT RequestId: abc-123  Duration: 142.33 ms  Billed Duration: 143 ms  Memory Size: 128 MB  Max Memory Used: 68 MB
```

The `request_id` in the application log matches the Lambda `RequestId`, enabling
cross-log correlation in CloudWatch Logs Insights.
