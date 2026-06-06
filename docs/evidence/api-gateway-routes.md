# Evidence: API Gateway Routes

## What to capture here

After a successful `sam deploy`, replace this file with a screenshot showing the five
routes registered in API Gateway. Instructions below.

---

## How to capture

1. Open the [AWS Console](https://console.aws.amazon.com/apigateway) and set the region to **eu-central-1**.
2. Click **APIs** in the left sidebar.
3. Click **device-registry-dev** (the HTTP API, not a REST API).
4. In the left sidebar, click **Routes**.
5. Take a screenshot of the routes panel. It should show:

   ```
   ANY    /$default
   POST   /devices
   GET    /devices
   GET    /devices/{deviceId}
   PATCH  /devices/{deviceId}
   DELETE /devices/{deviceId}
   ```

6. Save the screenshot as **`api-gateway-routes.png`** in this folder.
7. Update this file to reference it:

   ```markdown
   ![API Gateway Routes](api-gateway-routes.png)
   ```

---

## Retrieve the base URL from the CLI

```bash
aws cloudformation describe-stacks \
  --stack-name device-registry-dev \
  --region eu-central-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" \
  --output text
```

Expected output format:
```
https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
```

Store this URL — you need it for Postman validation and the integration tests.
