# Evidence: Postman Endpoint Validation

## What to capture

Use the Postman collection at `docs/postman/device-registry.postman_collection.json`
to validate all five endpoints against the deployed API.

### Screenshots needed

1. **POST /devices** — 201 Created response with full device JSON body
2. **GET /devices** — 200 OK with `items` array containing at least one device
3. **GET /devices/{deviceId}** — 200 OK for an existing device
4. **GET /devices/{deviceId}** — 404 Not Found for a random UUID
5. **PATCH /devices/{deviceId}** — 200 OK showing only the updated field changed
6. **POST /devices** with missing `name` — 400 Bad Request with `error` message
7. **DELETE /devices/{deviceId}** — 200 OK confirmation message
8. **GET /devices/{deviceId}** (same ID as above) — 404 confirming deletion

## Setup

1. Import `docs/postman/device-registry.postman_collection.json` into Postman
2. Set the `base_url` collection variable to your deployed API URL:
   ```
   https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
   ```
3. Run requests in the order above
4. Screenshot each response panel showing status code + body

## Placeholder

Replace this file with the actual screenshots once the API is deployed.
