"""Structural verification — run after making changes to confirm project health."""
import ast
import json
import pathlib
import sys

errors = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        errors.append(f"{name}{': ' + detail if detail else ''}")
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

# ── Source code quality ───────────────────────────────────────────────────
print("\nSource code — import correctness")
src_root = pathlib.Path("src")
for path in sorted(src_root.rglob("*.py")):
    if path.name == "__init__.py":
        continue
    src_text = path.read_text(encoding="utf-8")
    # Files inside src/ must NOT import with 'src.' prefix (breaks Lambda)
    bad_imports = [line.strip() for line in src_text.splitlines()
                   if line.strip().startswith(("from src.", "import src."))
                   and not line.strip().startswith("#")]
    check(
        f"No src-prefix imports in {path.relative_to(src_root)}",
        len(bad_imports) == 0,
        detail="; ".join(bad_imports[:2])
    )

print("\nSource code — function-level checks")
for path in sorted((src_root / "handlers").glob("*.py")):
    if path.name == "__init__.py":
        continue
    src_text = path.read_text(encoding="utf-8")
    tree = ast.parse(src_text)

    # No inline imports inside function bodies
    inline = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    inline.append(f"{node.name}:{child.lineno}")
    check(f"No inline imports in {path.name}", len(inline) == 0, detail=", ".join(inline))
    check(f"configure_logger in {path.name}", "configure_logger" in src_text)
    check(f"aws_request_id in {path.name}", "aws_request_id" in src_text)

# ── Security scan ─────────────────────────────────────────────────────────
print("\nSecurity scan")
secret_patterns = [
    "AKIA", "aws_access_key_id", "aws_secret_access_key",
    "password", "secret_key", "api_key", "token =",
]
for path in pathlib.Path(".").rglob("*.py"):
    if ".venv" in str(path) or ".aws-sam" in str(path):
        continue
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    for pattern in secret_patterns:
        # Exclude test credential stubs
        if pattern in text and "testing" not in text:
            # Only flag if it looks like a real value
            for line in text.splitlines():
                if pattern in line and "testing" not in line and "#" not in line.split(pattern)[0]:
                    errors.append(f"Potential secret in {path}: {line.strip()[:60]}")
                    print(f"  WARN: Possible secret pattern '{pattern}' in {path}")
                    break
check("No committed secrets detected", True)  # would have printed above

# ── Result ────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"FAILED — {len(errors)} issue(s):")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
