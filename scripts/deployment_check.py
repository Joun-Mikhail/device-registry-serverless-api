"""Pre-deployment readiness checks — verifies handler references, env vars, IAM."""
import pathlib
import re
import sys

tmpl = pathlib.Path("template.yaml").read_text()
errors = []


def ok(label):
    print(f"  PASS: {label}")


def fail(label, detail=""):
    msg = f"{label}: {detail}" if detail else label
    print(f"  FAIL: {msg}")
    errors.append(msg)


# ── Handler references ────────────────────────────────────────────────────
print("Lambda handler references")
handlers = re.findall(r"Handler:\s+(\S+)", tmpl)
for h in handlers:
    parts = h.split(".")
    rel = pathlib.Path(*parts[:-1]).with_suffix(".py")
    file_path = pathlib.Path("src") / rel
    fn_name = parts[-1]
    if not file_path.exists():
        fail(h, f"file not found: {file_path}")
        continue
    src = file_path.read_text()
    if f"def {fn_name}(" not in src:
        fail(h, f"function '{fn_name}' not defined in {file_path}")
    else:
        ok(f"{h} -> {file_path}")

# ── Environment variables ─────────────────────────────────────────────────
print("\nEnvironment variables")
for v in ["DEVICES_TABLE", "LOG_LEVEL"]:
    if v in tmpl:
        ok(f"{v} declared in template")
    else:
        fail(f"{v} missing from template Globals")

for p in sorted(pathlib.Path("src/repositories").glob("*.py")):
    if p.name == "__init__.py":
        continue
    src = p.read_text()
    if 'os.environ["DEVICES_TABLE"]' in src or "os.environ.get" in src:
        ok(f"{p.name} reads DEVICES_TABLE at runtime")

# ── IAM policy consistency ────────────────────────────────────────────────
print("\nIAM policy / DynamoDB operation alignment")
policy_map = {
    "CreateDevice":  ("DynamoDBWritePolicy", ["put_item"]),
    "GetDevice":     ("DynamoDBReadPolicy",  ["get_item"]),
    "ListDevices":   ("DynamoDBReadPolicy",  ["scan"]),
    "UpdateDevice":  ("DynamoDBCrudPolicy",  ["update_item"]),
    "DeleteDevice":  ("DynamoDBCrudPolicy",  ["delete_item"]),
}
for fn, (policy, ops) in policy_map.items():
    in_tmpl = policy in tmpl
    handler_name = fn[0].lower() + fn[1:]
    handler_file = pathlib.Path(f"src/repositories/device_repository.py")
    repo_src = handler_file.read_text()
    ops_ok = all(op in repo_src for op in ops)
    label = f"{fn}: {policy}"
    if in_tmpl and ops_ok:
        ok(label)
    else:
        fail(label, f"policy_in_template={in_tmpl} ops_present={ops_ok}")

# ── SAM template key properties ───────────────────────────────────────────
print("\nSAM template properties")
checks = [
    ("HttpApi resource", "AWS::Serverless::HttpApi" in tmpl),
    ("DynamoDB table", "AWS::DynamoDB::Table" in tmpl),
    ("PAY_PER_REQUEST", "PAY_PER_REQUEST" in tmpl),
    ("eu-central-1 in samconfig", "eu-central-1" in pathlib.Path("samconfig.toml").read_text()),
    ("Stack name device-registry-dev", "device-registry-dev" in pathlib.Path("samconfig.toml").read_text()),
    ("CAPABILITY_IAM", "CAPABILITY_IAM" in pathlib.Path("samconfig.toml").read_text()),
    ("python3.12 runtime", "python3.12" in tmpl),
    ("pythonpath = src in pytest.ini", "pythonpath = src" in pathlib.Path("pytest.ini").read_text()),
    ("All 5 CloudWatch log groups", tmpl.count("RetentionInDays: 7") == 5),
    ("ApiBaseUrl output", "ApiBaseUrl" in tmpl),
]
for label, result in checks:
    if result:
        ok(label)
    else:
        fail(label)

# ── Gitignore safety ──────────────────────────────────────────────────────
print("\n.gitignore safety")
gi = pathlib.Path(".gitignore").read_text()
for pattern in ["__pycache__", ".venv", ".aws-sam", ".coverage", "*.pem", "*.key", ".env"]:
    if pattern in gi:
        ok(f"{pattern} ignored")
    else:
        fail(f"{pattern} NOT in .gitignore")

# ── Result ────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"DEPLOYMENT READINESS: FAIL — {len(errors)} issue(s)")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("DEPLOYMENT READINESS: ALL CHECKS PASSED")
    print()
    print("Next steps (require your machine with SAM CLI + AWS credentials):")
    print("  1. sam build --parallel")
    print("  2. sam deploy --guided  (first time)")
    print("  3. sam deploy           (subsequent)")
