"""Structural verification — run after making changes to confirm project health."""
import ast
import json
import pathlib
import re
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
# Both src/ and tests/ must use bare imports (matching pythonpath=src and the
# Lambda runtime). A 'src.' prefix passes on Windows via pytest rootdir insertion
# but breaks on Linux/Lambda with ModuleNotFoundError: No module named 'src'.
for scan_root in (src_root, pathlib.Path("tests")):
    for path in sorted(scan_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        src_text = path.read_text(encoding="utf-8")
        bad_imports = [line.strip() for line in src_text.splitlines()
                       if ("from src." in line or "import src." in line
                           or '"src.' in line or "'src." in line)
                       and not line.strip().startswith("#")]
        check(
            f"No src-prefix imports in {path}",
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
# Flag a secret only when a sensitive key is ASSIGNED A HARDCODED STRING LITERAL,
# e.g.  password = "hunter2"  or  aws_secret_access_key="AKIA...".
# This deliberately ignores variable names that merely contain "token"/"key"
# (e.g. next_token = encode_token(...)) — those are logic, not secrets.
print("\nSecurity scan")
secret_assignment = re.compile(
    r'(aws_secret_access_key|aws_access_key_id|secret_key|api_key|password|passwd|client_secret)'
    r'\s*[:=]\s*["\'][^"\']+["\']',
    re.IGNORECASE,
)
akia_literal = re.compile(r'AKIA[0-9A-Z]{16}')
findings = []
for path in pathlib.Path(".").rglob("*.py"):
    if ".venv" in str(path) or ".aws-sam" in str(path):
        continue
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Ignore obvious test stubs (moto uses the literal "testing")
        if '"testing"' in line or "'testing'" in line:
            continue
        if secret_assignment.search(line) or akia_literal.search(line):
            findings.append(f"{path}:{lineno}: {stripped[:70]}")
for f in findings:
    print(f"  WARN: {f}")
    errors.append(f"Potential secret: {f}")
check("No committed secrets detected", len(findings) == 0)

# ── Result ────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"FAILED — {len(errors)} issue(s):")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
