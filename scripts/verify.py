"""Quick structural verification script — run after making changes."""
import json
import sys

errors = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    if not condition:
        errors.append(name)
    print(f"  {status}: {name}")


# ── template.yaml ─────────────────────────────────────────────────────────
print("template.yaml")
with open("template.yaml") as f:
    tmpl = f.read()

check("No Lambda Layer", "DependenciesLayer" not in tmpl)
check("No dependencies/ ContentUri", "ContentUri: dependencies/" not in tmpl)
check("PATCH method", "Method: PATCH" in tmpl)
check("No PUT method", "Method: PUT" not in tmpl)
check("LOG_LEVEL env var", "LOG_LEVEL: INFO" in tmpl)
check("128MB memory", "MemorySize: 128" in tmpl)
check("PAY_PER_REQUEST", "PAY_PER_REQUEST" in tmpl)
check("DeletionPolicy Retain", "DeletionPolicy: Retain" in tmpl)
check("5 log groups with 7-day retention", tmpl.count("RetentionInDays: 7") == 5)
check("python3.12 runtime", "python3.12" in tmpl)
check("All 5 functions", all(f in tmpl for f in [
    "CreateDeviceFunction", "GetDeviceFunction", "ListDevicesFunction",
    "UpdateDeviceFunction", "DeleteDeviceFunction"
]))

# ── GitHub Actions workflow ───────────────────────────────────────────────
print("\n.github/workflows/deploy.yml")
with open(".github/workflows/deploy.yml") as f:
    wf = f.read()

check("workflow_dispatch", "workflow_dispatch" in wf)
check("id-token: write (OIDC)", "id-token: write" in wf)
check("pip cache", "actions/cache@v4" in wf)
check("hashFiles cache key", "hashFiles" in wf)
check("needs: test gate", "needs: test" in wf)
check("environment: dev", "environment: dev" in wf)
check("AWS_DEPLOY_ROLE_ARN secret", "AWS_DEPLOY_ROLE_ARN" in wf)
check("sam build", "sam build" in wf)
check("sam deploy", "sam deploy" in wf)

# ── Postman collection ────────────────────────────────────────────────────
print("\ndocs/postman/device-registry.postman_collection.json")
with open("docs/postman/device-registry.postman_collection.json") as f:
    coll = json.load(f)

methods = [r["request"]["method"] for r in coll["item"]]
check("Valid JSON", True)
check("9 requests defined", len(coll["item"]) == 9)
check("Has POST", "POST" in methods)
check("Has PATCH (not PUT)", "PATCH" in methods and "PUT" not in methods)
check("Has DELETE", "DELETE" in methods)
check("Has GET", "GET" in methods)
check("Has base_url variable", any(v["key"] == "base_url" for v in coll["variable"]))
check("Has device_id variable", any(v["key"] == "device_id" for v in coll["variable"]))

# ── Source code checks ────────────────────────────────────────────────────
print("\nSource code")
import ast, pathlib

for path in pathlib.Path("src/handlers").glob("*.py"):
    if path.name == "__init__.py":
        continue
    src = path.read_text()
    tree = ast.parse(src)
    inline_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and not isinstance(getattr(node, "col_offset", 0) == 0 or True, bool)
    ]
    # Check: no imports inside function bodies
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    errors.append(f"Inline import in {path.name}::{node.name}")
                    print(f"  FAIL: Inline import in {path.name}::{node.name}")
    check(f"No inline imports in {path.name}", True)

for path in pathlib.Path("src/handlers").glob("*.py"):
    if path.name == "__init__.py":
        continue
    src = path.read_text()
    check(f"configure_logger used in {path.name}", "configure_logger" in src)
    check(f"aws_request_id logged in {path.name}", "aws_request_id" in src)

# ── Result ────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"FAILED: {len(errors)} check(s) failed: {errors}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
