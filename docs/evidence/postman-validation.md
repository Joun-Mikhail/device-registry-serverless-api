# Evidence: Postman Endpoint Validation

## What to capture here

After deploying the API, use the Postman collection to validate every endpoint and
replace this file with screenshots of the results.

---

## Setup

1. Open Postman.
2. Click **Import** → select `docs/postman/device-registry.postman_collection.json`.
3. Click the collection name → **Variables** tab.
4. Set `base_url` to your deployed API URL:
   ```
   https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
   ```
5. Save.

---

## Screenshots to take (in order)

Run each request in this sequence. Each one auto-populates `{{device_id}}` for
subsequent requests.

| # | Screenshot filename | Request | Expected status |
|---|---|---|---|
| 1 | `postman-01-create-201.png` | POST /devices | 201 Created |
| 2 | `postman-02-list-200.png` | GET /devices | 200 OK |
| 3 | `postman-03-get-200.png` | GET /devices/{{device_id}} | 200 OK |
| 4 | `postman-04-get-404.png` | GET /devices/00000000-... | 404 Not Found |
| 5 | `postman-05-patch-200.png` | PATCH /devices/{{device_id}} | 200 OK |
| 6 | `postman-06-create-400-name.png` | POST /devices (missing name) | 400 Bad Request |
| 7 | `postman-07-create-400-type.png` | POST /devices (invalid type) | 400 Bad Request |
| 8 | `postman-08-delete-200.png` | DELETE /devices/{{device_id}} | 200 OK |
| 9 | `postman-09-get-404-deleted.png` | GET /devices/{{device_id}} | 404 Not Found |

For each screenshot, show the **full Postman response panel** including:
- Request method + URL
- Status code (e.g. `200 OK`)
- Response body (JSON)
- Test results tab (all green)

---

## Run the full collection automatically

In Postman, click the **...** menu on the collection → **Run collection**.
Screenshot the Collection Runner summary showing all 9 requests passing their
automated test assertions.

Save as `postman-collection-runner.png`.
