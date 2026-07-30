#!/usr/bin/env python3
"""Run the API locally, with no AWS account required.

Starts an in-memory DynamoDB (via moto), creates the table defined in
template.yaml, and serves the real Lambda handlers over HTTP. Requests are
translated into the API Gateway HTTP API event shape the handlers expect, so the
code exercised here is exactly the code that would run in Lambda — only the
DynamoDB backend is simulated.

    python scripts/local_server.py            # http://127.0.0.1:8000
    python scripts/local_server.py --port 9000

Then, in another terminal:

    curl -X POST http://127.0.0.1:8000/devices \\
      -H 'Content-Type: application/json' \\
      -d '{"name": "Temp Sensor A", "type": "sensor", "location": "Floor 2"}'
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

TABLE_NAME = "device-registry-dev"
REGION = "eu-central-1"

# moto intercepts boto3 at the client layer, so these must be set before any
# boto3 client is constructed. They are placeholders; no real AWS call is made.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", REGION)
os.environ.setdefault("DEVICES_TABLE", TABLE_NAME)

import boto3
from moto import mock_aws

# Route table mirrors the Events defined for each function in template.yaml.
COLLECTION = re.compile(r"^/devices/?$")
ITEM = re.compile(r"^/devices/(?P<deviceId>[^/]+)/?$")


def _create_table() -> None:
    """Create the table exactly as template.yaml declares it, including the GSI."""
    client = boto3.client("dynamodb", region_name=REGION)
    client.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "deviceId", "AttributeType": "S"},
            {"AttributeName": "type", "AttributeType": "S"},
            {"AttributeName": "createdAt", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "deviceId", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "type-createdAt-index",
                "KeySchema": [
                    {"AttributeName": "type", "KeyType": "HASH"},
                    {"AttributeName": "createdAt", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )


def _resolve(method: str, path: str):
    """Map an HTTP method and path to a handler and its path parameters."""
    from handlers import (
        create_device,
        delete_device,
        get_device,
        list_devices,
        update_device,
    )

    if COLLECTION.match(path):
        if method == "POST":
            return create_device.handler, {}
        if method == "GET":
            return list_devices.handler, {}
        return None, {}

    item = ITEM.match(path)
    if item:
        params = item.groupdict()
        if method == "GET":
            return get_device.handler, params
        if method == "PATCH":
            return update_device.handler, params
        if method == "DELETE":
            return delete_device.handler, params
    return None, {}


def _build_event(method: str, path: str, query: str, path_params: dict, body: str | None) -> dict:
    """Construct the API Gateway HTTP API event shape the handlers consume."""
    parsed: dict[str, str] = {}
    if query:
        for pair in query.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                parsed[k] = v
    return {
        "httpMethod": method,
        "rawPath": path,
        # API Gateway sends null rather than {} when there are no values.
        "pathParameters": path_params or None,
        "queryStringParameters": parsed or None,
        "body": body,
        "requestContext": {"requestId": "local", "http": {"method": method, "path": path}},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DeviceRegistryLocal/1.0"

    # Set from --api-key. None means the API is open, matching a stack deployed
    # before the authorizer existed.
    api_key: str | None = None

    def _authorized(self) -> bool:
        """Mirror the deployed Lambda authorizer: same header, same comparison."""
        if self.api_key is None:
            return True
        presented = None
        for name in self.headers:
            if name.lower() == "x-api-key":
                presented = self.headers[name]
                break
        return bool(presented) and hmac.compare_digest(presented, self.api_key)

    def _dispatch(self, method: str) -> None:
        raw = self.path.split("?", 1)
        path, query = raw[0], (raw[1] if len(raw) > 1 else "")

        if not self._authorized():
            self._respond(
                401,
                json.dumps({"error": {"code": "UNAUTHORIZED", "message": "A valid x-api-key header is required."}}),
            )
            return

        handler, path_params = _resolve(method, path)
        if handler is None:
            self._respond(
                404,
                json.dumps({"error": {"code": "NOT_FOUND", "message": f"No route for {method} {path}."}}),
            )
            return

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else None

        event = _build_event(method, path, query, path_params, body)
        result = handler(event, None)
        self._respond(result["statusCode"], result["body"], result.get("headers", {}))

    def _respond(self, status: int, body: str, headers: dict | None = None) -> None:
        payload = (body or "").encode("utf-8")
        self.send_response(status)
        for key, value in (headers or {"Content-Type": "application/json"}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self._respond(
            204,
            "",
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
            },
        )

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--seed", action="store_true", help="Insert a few example devices on startup.")
    parser.add_argument(
        "--api-key",
        help="Require this value in the x-api-key header, mirroring the deployed "
             "Lambda authorizer. Omit to leave the local API open.",
    )
    args = parser.parse_args()
    Handler.api_key = args.api_key

    with mock_aws():
        _create_table()

        if args.seed:
            from handlers import create_device

            examples = [
                {"name": "Temp Sensor A", "type": "sensor", "location": "Floor 2"},
                {"name": "Main Gateway", "type": "gateway", "location": "Server Room"},
                {"name": "Door Controller", "type": "controller", "status": "maintenance"},
            ]
            for payload in examples:
                create_device.handler(
                    _build_event("POST", "/devices", "", {}, json.dumps(payload)), None
                )
            print(f"Seeded {len(examples)} example devices.")

        server = HTTPServer((args.host, args.port), Handler)
        print(f"Device Registry API listening on http://{args.host}:{args.port}")
        print("DynamoDB is simulated in memory (moto). Data is lost on exit.")
        if args.api_key:
            print("Authentication is ON: send  -H 'x-api-key: <key>'  with every request.")
        else:
            print("Authentication is OFF. Pass --api-key to require one.")
        print("Press Ctrl+C to stop.\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
