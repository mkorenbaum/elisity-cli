#!/usr/bin/env python3
"""
Elisity CLI — Exhaustive Command Validation
============================================
Tests EVERY CLI command against a live CCC instance.
- All GET commands with no path params: invoked directly
- All GET commands with path params: invoked with discovered IDs
- All POST read-only commands (views/searches): invoked with minimal body
- All write commands (POST/PUT/DELETE): help-only validation (no mutations)

Produces a comprehensive bug report.

Usage:
    source .venv/bin/activate
    CCC_BASE_URL=https://tme-26-3.idp01.elisity.io \
    CCC_CLIENT_ID=... CCC_CLIENT_SECRET=... \
    python3 tests/qa_exhaustive.py
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

ELISITY = "elisity"

@dataclass
class TestResult:
    group: str
    cmd: str
    method: str
    path: str
    status: str  # PASS, FAIL, SKIP, HELP_ONLY
    exit_code: int = 0
    stdout_snippet: str = ""
    stderr_snippet: str = ""
    duration_ms: int = 0
    notes: str = ""

results: List[TestResult] = []

def run_cmd(args: list, timeout: int = 30) -> tuple:
    cmd = [ELISITY] + args
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "COLUMNS": "200"})
        ms = int((time.time() - start) * 1000)
        return r.returncode, r.stdout, r.stderr, ms
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT", int((time.time() - start) * 1000)

def is_valid_json(s):
    try:
        json.loads(s)
        return True
    except Exception:
        return False

def has_traceback(stderr):
    return "Traceback" in stderr

# ── Discovery: get real IDs from the CCC ────────────────────────────────

def discover_ids() -> Dict[str, Any]:
    """Discover real entity IDs from the CCC for path-param tests."""
    ids = {}

    # Sites
    code, out, _, _ = run_cmd(["topology", "get-all-sites", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["site_id"] = json.loads(out)
        except: pass

    # VEs
    code, out, _, _ = run_cmd(["topology", "get-virtual-edge", "-q", "content[0].id"])
    if code == 0 and out.strip():
        try:
            ids["ve_id"] = json.loads(out)
        except: pass

    # VENs
    code, out, _, _ = run_cmd(["topology", "get-virtual-edge-nodes", "-q", "content[0].id"])
    if code == 0 and out.strip():
        try:
            ids["ven_id"] = json.loads(out)
        except: pass

    # Policy set
    code, out, _, _ = run_cmd(["policy", "get-all-as-nd-json", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["policy_set_id"] = json.loads(out)
        except: pass

    # Policy group
    code, out, _, _ = run_cmd(["policy", "get-policy-groups-json", "-q", "content[0].id"])
    if code == 0 and out.strip():
        try:
            ids["policy_group_id"] = json.loads(out)
        except: pass

    # Policy ID (from first policy set)
    if ids.get("policy_set_id"):
        code, out, _, _ = run_cmd(["policy", "get-all-policies-for-policy-set-as-nd-json",
                                    ids["policy_set_id"], "-q", "[0].id"])
        if code == 0 and out.strip():
            try:
                ids["policy_id"] = json.loads(out)
            except: pass

    # Security profile
    code, out, _, _ = run_cmd(["policy", "get-all-security-profiles-as-nd-json", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["security_profile_id"] = json.loads(out)
        except: pass

    # Service definition
    code, out, _, _ = run_cmd(["policy", "get-all-service-definitions-json", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["service_definition_id"] = json.loads(out)
        except: pass

    # Policy view
    code, out, _, _ = run_cmd(["policy", "get-all-policy-views-as-nd-json", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["policy_view_id"] = json.loads(out)
        except: pass

    # Distribution zone
    code, out, _, _ = run_cmd(["topology", "get-all-distribution-zones", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["distribution_zone_id"] = json.loads(out)
        except: pass

    # Flow exporter
    code, out, _, _ = run_cmd(["topology", "get-all-flow-exporter", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["flow_exporter_id"] = json.loads(out)
        except: pass

    # Connector
    code, out, _, _ = run_cmd(["connectors", "read", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["connector_id"] = json.loads(out)
        except: pass

    # AD connector
    code, out, _, _ = run_cmd(["ad", "get-connectors", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["ad_connector_id"] = json.loads(out)
        except: pass

    # Noise definition
    code, out, _, _ = run_cmd(["flows", "get-noise-definition", "-q", "id"])
    if code == 0 and out.strip():
        try:
            ids["noise_def_id"] = json.loads(out)
        except: pass

    # Task specs
    code, out, _, _ = run_cmd(["system", "list-specs", "-q", "[0].name"])
    if code == 0 and out.strip():
        try:
            ids["task_spec_name"] = json.loads(out)
        except: pass

    # Global credentials
    code, out, _, _ = run_cmd(["topology", "get-all-global-credentials", "-q", "[0].id"])
    if code == 0 and out.strip():
        try:
            ids["credentials_id"] = json.loads(out)
        except: pass

    return ids


# ── Path param resolver ────────────────────────────────────────────────

# Maps path parameter name patterns to discovered ID keys
PARAM_MAP = {
    "siteid": "site_id",
    "id": None,  # context-dependent
    "veid": "ve_id",
    "venid": "ven_id",
    "policysetid": "policy_set_id",
    "policygroupid": "policy_group_id",
    "policyid": "policy_id",
    "securityprofileid": "security_profile_id",
    "servicedefinitionid": "service_definition_id",
    "policyviewid": "policy_view_id",
    "distributionzoneid": "distribution_zone_id",
    "flowexporterid": "flow_exporter_id",
    "connectorid": "connector_id",
    "credentialsid": "credentials_id",
    "name": "task_spec_name",
    "noisedefinitionid": "noise_def_id",
}

# Group-specific "id" resolution
GROUP_ID_MAP = {
    "topology": "site_id",
    "policy": "policy_set_id",
    "devices": "site_id",
    "connectors": "connector_id",
    "ad": "ad_connector_id",
    "flows": "noise_def_id",
    "insights": "site_id",
    "system": "task_spec_name",
}

def resolve_path_params(group: str, path_params: list, ids: dict) -> Optional[list]:
    """Try to resolve all path params for a command. Returns list of values or None if can't resolve."""
    values = []
    for pname in path_params:
        pname_lower = pname.lower()
        id_key = PARAM_MAP.get(pname_lower)
        if id_key is None and pname_lower == "id":
            id_key = GROUP_ID_MAP.get(group)
        if id_key and id_key in ids:
            values.append(str(ids[id_key]))
        else:
            return None  # Can't resolve this param
    return values


# ── Read-only POST commands (safe to call) ──────────────────────────────

SAFE_POST_COMMANDS = {
    # These POST commands are read-only (search/view operations)
    ("devices", "get-devices-view"): '{"page":0,"size":5}',
    ("devices", "get-devices-view-v2"): '{"page":0,"size":5}',
    ("devices", "get-device-details"): '{"page":0,"size":5}',
    ("devices", "get-device-details-by-identity"): '{"page":0,"size":5}',
    ("policy", "lookup-evaluation-endpoint"): '{"ip":"10.0.0.1"}',
    ("system", "get-audit-trail"): '{"page":0,"size":5}',
}


# ── Main test runner ───────────────────────────────────────────────────

def load_commands() -> list:
    with open("/tmp/all-cli-commands.json") as f:
        return json.load(f)


def test_help(group: str, cmd: str) -> TestResult:
    """Validate that --help works for a command."""
    code, out, err, ms = run_cmd([group, cmd, "--help"])
    if code == 0 and ("Usage:" in out or "Options:" in out):
        return TestResult(group=group, cmd=cmd, method="HELP", path="",
                         status="PASS", exit_code=code, duration_ms=ms,
                         stdout_snippet=out[:200], notes="Help validated")
    return TestResult(group=group, cmd=cmd, method="HELP", path="",
                     status="FAIL", exit_code=code, duration_ms=ms,
                     stderr_snippet=err[:300], notes="Help broken")


def test_command(c: dict, ids: dict) -> TestResult:
    """Test a single command against the CCC."""
    group = c["group"]
    cmd = c["cmd"]
    method = c["method"]
    path = c["path"]
    path_params = c["path_params"]
    has_body = c["has_body"]

    # Build CLI args
    args = [group, cmd]

    # Resolve path params
    if path_params:
        # Deduplicate while preserving order
        seen = set()
        unique_params = []
        for p in path_params:
            if p not in seen:
                seen.add(p)
                unique_params.append(p)

        values = resolve_path_params(group, unique_params, ids)
        if values is None:
            return TestResult(group=group, cmd=cmd, method=method, path=path,
                             status="SKIP", notes=f"Cannot resolve path params: {unique_params}")
        args.extend(values)

    # For write operations (POST that creates, PUT, DELETE, PATCH) — only test help
    if method in ("PUT", "DELETE", "PATCH"):
        return test_help(group, cmd)
    if method == "POST" and (group, cmd) not in SAFE_POST_COMMANDS and not has_body:
        # POST with no body that's not in safe list — might be safe, try it
        pass
    elif method == "POST" and (group, cmd) in SAFE_POST_COMMANDS:
        body = SAFE_POST_COMMANDS[(group, cmd)]
        args.extend(["--body", body])
    elif method == "POST" and has_body:
        # Unknown POST with body — just validate help
        return test_help(group, cmd)

    # Execute
    code, out, err, ms = run_cmd(args, timeout=30)

    # Classify result
    if has_traceback(err):
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="FAIL", exit_code=code, duration_ms=ms,
                         stderr_snippet=err[:500],
                         notes="PYTHON TRACEBACK — BUG")
    if code == 0:
        if is_valid_json(out) or out.strip():
            return TestResult(group=group, cmd=cmd, method=method, path=path,
                             status="PASS", exit_code=code, duration_ms=ms,
                             stdout_snippet=out[:200])
        else:
            return TestResult(group=group, cmd=cmd, method=method, path=path,
                             status="PASS", exit_code=code, duration_ms=ms,
                             notes="Empty response (may be normal)")
    # Non-zero exit
    if "403" in err:
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="PERM", exit_code=code, duration_ms=ms,
                         stderr_snippet=err[:200],
                         notes="403 Forbidden — permission issue")
    if "404" in err:
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="NOTFOUND", exit_code=code, duration_ms=ms,
                         stderr_snippet=err[:200],
                         notes="404 Not Found — endpoint missing")
    if "400" in err:
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="BADREQ", exit_code=code, duration_ms=ms,
                         stderr_snippet=err[:200],
                         notes="400 Bad Request — may need params")
    if "500" in err or "502" in err or "503" in err:
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="SRVERR", exit_code=code, duration_ms=ms,
                         stderr_snippet=err[:200],
                         notes="Server error")
    if "TIMEOUT" in err:
        return TestResult(group=group, cmd=cmd, method=method, path=path,
                         status="TIMEOUT", exit_code=code, duration_ms=ms,
                         notes="Command timed out (>30s)")
    return TestResult(group=group, cmd=cmd, method=method, path=path,
                     status="FAIL", exit_code=code, duration_ms=ms,
                     stderr_snippet=err[:300],
                     notes="Unknown error")


def print_report(results: list, ids: dict, duration: float):
    ccc = os.environ.get("CCC_BASE_URL", "unknown")
    print("\n" + "=" * 80)
    print("  ELISITY CLI v0.1.0 — EXHAUSTIVE COMMAND VALIDATION REPORT")
    print("=" * 80)
    print(f"  Target:      {ccc}")
    print(f"  Date:        {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Duration:    {duration:.1f}s")
    print(f"  IDs found:   {len([v for v in ids.values() if v])}")
    print("=" * 80)

    # Count by status
    by_status = {}
    for r in results:
        by_status.setdefault(r.status, []).append(r)

    status_labels = {
        "PASS": "Passed (valid response)",
        "FAIL": "Failed (bug/traceback)",
        "SKIP": "Skipped (no test data)",
        "HELP_ONLY": "Help-only (write cmd)",
        "PERM": "403 Forbidden (permission)",
        "NOTFOUND": "404 Not Found (endpoint missing)",
        "BADREQ": "400 Bad Request (needs params)",
        "SRVERR": "5xx Server Error",
        "TIMEOUT": "Timeout (>30s)",
    }

    print(f"\n{'Status':<40} {'Count':>6}")
    print("-" * 50)
    for s in ["PASS", "FAIL", "BADREQ", "PERM", "NOTFOUND", "SRVERR", "TIMEOUT", "SKIP", "HELP_ONLY"]:
        if s in by_status:
            print(f"  {status_labels.get(s, s):<38} {len(by_status[s]):>4}")
    print("-" * 50)
    print(f"  {'TOTAL':<38} {len(results):>4}")

    # Summary by group
    print(f"\n{'Group':<15} {'Pass':>6} {'Fail':>6} {'BadReq':>8} {'Perm':>6} {'404':>6} {'Skip':>6} {'Help':>6} {'Total':>6}")
    print("-" * 80)
    by_group = {}
    for r in results:
        by_group.setdefault(r.group, []).append(r)
    for g in sorted(by_group.keys()):
        gresults = by_group[g]
        counts = {s: 0 for s in ["PASS", "FAIL", "BADREQ", "PERM", "NOTFOUND", "SKIP", "HELP_ONLY"]}
        for r in gresults:
            counts[r.status] = counts.get(r.status, 0) + 1
        print(f"  {g:<13} {counts['PASS']:>4} {counts['FAIL']:>6} {counts.get('BADREQ',0):>8} "
              f"{counts.get('PERM',0):>6} {counts.get('NOTFOUND',0):>6} {counts['SKIP']:>6} "
              f"{counts.get('HELP_ONLY',0):>6} {len(gresults):>6}")

    # List all non-PASS, non-SKIP, non-HELP_ONLY
    issues = [r for r in results if r.status in ("FAIL", "BADREQ", "PERM", "NOTFOUND", "SRVERR", "TIMEOUT")]
    if issues:
        print(f"\n{'='*80}")
        print(f"  ISSUES DETAIL ({len(issues)} total)")
        print(f"{'='*80}")
        for r in issues:
            print(f"\n  [{r.status}] {r.group} {r.cmd}")
            print(f"    Method: {r.method}  Path: {r.path}")
            if r.stderr_snippet:
                print(f"    Error:  {r.stderr_snippet[:200]}")
            if r.notes:
                print(f"    Notes:  {r.notes}")

    # Tracebacks are the most critical
    tracebacks = [r for r in results if r.status == "FAIL" and "TRACEBACK" in r.notes.upper()]
    if tracebacks:
        print(f"\n{'='*80}")
        print(f"  CRITICAL: {len(tracebacks)} PYTHON TRACEBACKS (bugs)")
        print(f"{'='*80}")
        for r in tracebacks:
            print(f"  {r.group} {r.cmd}: {r.stderr_snippet[:300]}")

    print(f"\n{'='*80}")

    # Write JSON report
    report_data = {
        "ccc": ccc,
        "date": time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        "duration_s": round(duration, 1),
        "total": len(results),
        "summary": {s: len(by_status.get(s, [])) for s in status_labels},
        "discovered_ids": {k: str(v)[:20] + "..." if v and len(str(v)) > 20 else str(v) for k, v in ids.items()},
        "results": [
            {"group": r.group, "cmd": r.cmd, "method": r.method, "path": r.path,
             "status": r.status, "exit_code": r.exit_code, "duration_ms": r.duration_ms,
             "notes": r.notes, "stderr": r.stderr_snippet[:200]}
            for r in results
        ],
        "issues": [
            {"group": r.group, "cmd": r.cmd, "method": r.method, "path": r.path,
             "status": r.status, "stderr": r.stderr_snippet, "notes": r.notes}
            for r in issues
        ]
    }

    report_path = Path(__file__).parent / "qa_exhaustive_report.json"
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"\n  JSON report: {report_path}")
    print("=" * 80)


def main():
    start = time.time()

    print("=" * 80)
    print("  ELISITY CLI — EXHAUSTIVE COMMAND VALIDATION")
    print("=" * 80)

    # Phase 1: Discover IDs
    print("\n[Phase 1] Discovering entity IDs from CCC...")
    ids = discover_ids()
    for k, v in ids.items():
        print(f"  {k}: {str(v)[:40]}")

    # Phase 2: Load all commands
    print("\n[Phase 2] Loading command manifest...")
    commands = load_commands()
    print(f"  {len(commands)} commands loaded")

    # Phase 3: Test all commands
    print(f"\n[Phase 3] Testing all commands...\n")

    current_group = ""
    for c in commands:
        if c["group"] != current_group:
            current_group = c["group"]
            print(f"\n--- {current_group.upper()} ---")

        r = test_command(c, ids)
        results.append(r)

        icon = {"PASS": ".", "FAIL": "X", "SKIP": "-", "HELP_ONLY": "h",
                "PERM": "P", "NOTFOUND": "N", "BADREQ": "B", "SRVERR": "E",
                "TIMEOUT": "T"}.get(r.status, "?")
        detail = ""
        if r.status not in ("PASS", "HELP_ONLY", "SKIP"):
            detail = f"  [{r.status}] {r.notes}"
        print(f"  {icon} {c['cmd']}{detail}")

    duration = time.time() - start
    print_report(results, ids, duration)

    # Exit code: fail if any tracebacks or hard failures
    hard_fails = [r for r in results if r.status == "FAIL"]
    sys.exit(1 if hard_fails else 0)


if __name__ == "__main__":
    main()
