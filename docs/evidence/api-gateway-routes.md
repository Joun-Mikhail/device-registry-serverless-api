# Evidence: API Gateway Routes

## What to capture

After a successful `sam deploy`, take a screenshot of the API Gateway console showing:

1. The HTTP API name (`device-registry-dev` stage)
2. The route list — five routes should be present:

   ```
   POST   /devices
   GET    /devices
   GET    /devices/{deviceId}
   PATCH  /devices/{deviceId}
   DELETE /devices/{deviceId}
   ```

3. The Invoke URL (base URL for all requests)

## How to retrieve the URL from the CLI

```bash
aws cloudformation describe-stacks \
  --stack-name device-registry-dev \
  --region eu-central-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" \
  --output text
```

## Placeholder

Replace this file with a screenshot (`api-gateway-routes.png`) once the stack is deployed.
The screenshot should show all five routes listed in the AWS Console under
**API Gateway → APIs → device-registry-dev → Routes**.
