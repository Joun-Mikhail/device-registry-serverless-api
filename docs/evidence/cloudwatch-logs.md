# Evidence: CloudWatch Logs

## What to capture

After sending at least one request to each endpoint, take screenshots showing:

1. **Log group list** — five log groups with 7-day retention:
   - `/aws/lambda/device-registry-create-dev`
   - `/aws/lambda/device-registry-get-dev`
   - `/aws/lambda/device-registry-list-dev`
   - `/aws/lambda/device-registry-update-dev`
   - `/aws/lambda/device-registry-delete-dev`

2. **A log stream from CreateDevice** showing:
   - The `START` line from Lambda runtime
   - The `CreateDevice invoked request_id=<uuid>` INFO line
   - The `END` and `REPORT` lines (including duration and memory used)

3. **A 404 response log** from GetDevice showing a request for a non-existent ID.

## How to tail logs from the CLI

```bash
# Requires AWS SAM CLI
sam logs --stack-name device-registry-dev --name CreateDeviceFunction --tail

# Or with AWS CLI directly
aws logs tail /aws/lambda/device-registry-create-dev --follow
```

## Placeholder

Replace this file with screenshots once the stack is deployed and has received traffic.
Logs confirm that:
- CloudWatch log groups were created with correct retention
- LOG_LEVEL configuration is working
- Request IDs appear in log lines for correlation
