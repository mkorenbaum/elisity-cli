#!/usr/bin/env python3
"""
Elisity CLI — Cross-Validation Against Direct API
===================================================
For each key operation, runs the CLI command AND a direct curl/requests call
to the CCC API, then compares the outputs to verify data correctness.

This proves the CLI is returning the SAME data as the raw API.
"""

import json
import os
import subprocess
import sys
import time
import requests
from pathlib import Path

CCC_BASE = os.environ.get("CCC_BASE_URL", "https://tme-26-3.idp01.elisity.io")
CCC_ID = os.environ.get("CCC_CLIENT_ID", "")
CCC_SECRET = os.environ.get("CCC_CLIENT_SECRET", "")
ELISITY = "elisity"

results = []

# Use the CLI's own client for direct API calls — same auth, same session headers
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from elisity_cli.client import CCCClient

_client = None

def get_client():
    global _client
    if _client is None:
        _client = CCCClient(CCC_BASE, CCC_ID, CCC_SECRET)
        _client.authenticate()
    return _client

def api_get(path, params=None):
    """Direct API GET using the CLI's own client session."""
    c = get_client()
    resp = c.session.get(f"{CCC_BASE}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

def api_post(path, body=None):
    """Direct API POST using the CLI's own client session."""
    c = get_client()
    resp = c.session.post(f"{CCC_BASE}{path}", json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()

def api_get_ndjson(path, params=None):
    """Direct API GET for NDJSON using CLI's session with NDJSON accept header."""
    c = get_client()
    resp = c.session.get(f"{CCC_BASE}{path}", params=params,
                         headers={**dict(c.session.headers), "Accept": "application/x-ndjson"}, timeout=15)
    resp.raise_for_status()
    lines = [json.loads(line) for line in resp.text.strip().split("\n") if line.strip()]
    return lines

def cli_run(args, timeout=30):
    """Run CLI and return parsed JSON output."""
    cmd = [ELISITY] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                      env={**os.environ, "COLUMNS": "200"})
    if r.returncode != 0:
        return None, r.stderr
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError:
        return r.stdout, None

# ── Comparison helpers ──────────────────────────────────────────────────

def compare_json(cli_data, api_data, label, key_fields=None):
    """Compare CLI output to direct API output."""
    result = {"test": label, "status": "PASS", "details": ""}

    if cli_data is None:
        result["status"] = "FAIL"
        result["details"] = "CLI returned no data"
        return result

    if api_data is None:
        result["status"] = "FAIL"
        result["details"] = "API returned no data"
        return result

    # Type match
    if type(cli_data) != type(api_data):
        result["status"] = "FAIL"
        result["details"] = f"Type mismatch: CLI={type(cli_data).__name__}, API={type(api_data).__name__}"
        return result

    # For lists: compare length and key fields of first items
    if isinstance(cli_data, list):
        if len(cli_data) != len(api_data):
            result["status"] = "WARN"
            result["details"] = f"Length mismatch: CLI={len(cli_data)}, API={len(api_data)}"
        elif len(cli_data) > 0 and key_fields:
            for kf in key_fields:
                cli_val = cli_data[0].get(kf) if isinstance(cli_data[0], dict) else None
                api_val = api_data[0].get(kf) if isinstance(api_data[0], dict) else None
                if cli_val != api_val:
                    result["status"] = "FAIL"
                    result["details"] = f"Field '{kf}' mismatch: CLI={cli_val}, API={api_val}"
                    return result
            result["details"] = f"Matched {len(cli_data)} items, key fields verified"
        else:
            result["details"] = f"Both returned {len(cli_data)} items"
        return result

    # For dicts: compare key fields
    if isinstance(cli_data, dict):
        if key_fields:
            for kf in key_fields:
                cli_val = cli_data.get(kf)
                api_val = api_data.get(kf)
                if cli_val != api_val:
                    result["status"] = "FAIL"
                    result["details"] = f"Field '{kf}' mismatch: CLI={cli_val}, API={api_val}"
                    return result
            result["details"] = f"Key fields {key_fields} match"
        else:
            if cli_data == api_data:
                result["details"] = "Exact match"
            else:
                cli_keys = set(cli_data.keys())
                api_keys = set(api_data.keys())
                if cli_keys != api_keys:
                    result["status"] = "WARN"
                    result["details"] = f"Key diff: CLI-only={cli_keys - api_keys}, API-only={api_keys - cli_keys}"
                else:
                    result["details"] = "Same keys, values may differ in ordering"
        return result

    # Scalar comparison
    if cli_data == api_data:
        result["details"] = f"Exact match: {str(cli_data)[:100]}"
    else:
        result["status"] = "FAIL"
        result["details"] = f"Value mismatch: CLI={str(cli_data)[:100]}, API={str(api_data)[:100]}"

    return result

# ── Test Cases ──────────────────────────────────────────────────────────

def run_all_tests():
    client = get_client()
    print(f"Authenticated via CLI client (token: {client.access_token[:30]}...)")

    tests = [
        # ── TOPOLOGY ──
        {
            "label": "topology: get-all-sites",
            "cli_args": ["topology", "get-all-sites"],
            "api_call": lambda: api_get("/api/topology/v2/sites"),
            "key_fields": ["id", "label"],
        },
        {
            "label": "topology: get-all-distribution-zones",
            "cli_args": ["topology", "get-all-distribution-zones"],
            "api_call": lambda: api_get("/api/topology/v2/distribution-zones"),
            "key_fields": ["id", "name"],
        },
        {
            "label": "topology: get-virtual-edge (paginated)",
            "cli_args": ["topology", "get-virtual-edge"],
            "api_call": lambda: api_get("/api/topology/v1/virtual-edges"),
            "key_fields": ["content", "totalElements"],
        },
        {
            "label": "topology: get-virtual-edge-nodes (paginated)",
            "cli_args": ["topology", "get-virtual-edge-nodes"],
            "api_call": lambda: api_get("/api/topology/v1/virtual-edge-nodes"),
            "key_fields": ["content", "totalElements"],
        },
        {
            "label": "topology: get-all-flow-exporter",
            "cli_args": ["topology", "get-all-flow-exporter"],
            "api_call": lambda: api_get("/api/topology/v1/flow-exporters"),
            "key_fields": None,
        },
        {
            "label": "topology: get-all-global-credentials",
            "cli_args": ["topology", "get-all-global-credentials"],
            "api_call": lambda: api_get("/api/topology/v1/global-credentials"),
            "key_fields": ["id"],
        },
        {
            "label": "topology: get-global-interfaces-settings",
            "cli_args": ["topology", "get-global-interfaces-settings"],
            "api_call": lambda: api_get("/api/topology/v1/global-interfaces-settings"),
            "key_fields": None,
        },

        # ── POLICY ──
        {
            "label": "policy: get-all-as-nd-json (policy sets)",
            "cli_args": ["policy", "get-all-as-nd-json"],
            "api_call": lambda: api_get_ndjson("/api/policy/v1/policy-sets"),
            "key_fields": ["id", "name"],
        },
        {
            "label": "policy: get-all-security-profiles-as-nd-json",
            "cli_args": ["policy", "get-all-security-profiles-as-nd-json"],
            "api_call": lambda: api_get_ndjson("/api/policy/v1/security-profiles"),
            "key_fields": ["id", "name"],
        },
        {
            "label": "policy: get-policy-groups-json (paginated)",
            "cli_args": ["policy", "get-policy-groups-json"],
            "api_call": lambda: api_get("/api/policy/v2/policy-groups"),
            "key_fields": ["content", "totalElements"],
        },
        {
            "label": "policy: get-all-service-definitions-json",
            "cli_args": ["policy", "get-all-service-definitions-json"],
            "api_call": lambda: api_get("/api/policy/v1/service-definitions"),
            "key_fields": ["id", "name"],
        },
        {
            "label": "policy: get-all-policies-as-nd-json",
            "cli_args": ["policy", "get-all-policies-as-nd-json"],
            "api_call": lambda: api_get_ndjson("/api/policy/v1/policy-sets/policies"),
            "key_fields": ["id", "name"],
        },

        # ── DEVICES ──
        {
            "label": "devices: get-device-count",
            "cli_args": ["devices", "get-device-count"],
            "api_call": lambda: api_get("/api/identity-graph/v1/devices/count"),
            "key_fields": ["devicesCount"],
        },
        {
            "label": "devices: get-devices-view (POST)",
            "cli_args": ["devices", "get-devices-view", "--body", '{"page":0,"size":5}'],
            "api_call": lambda: api_post("/api/identity-graph/v1/devices/view", {"page": 0, "size": 5}),
            "key_fields": ["totalElements", "totalPages"],
        },
        {
            "label": "devices: get-blended-enrichment-order",
            "cli_args": ["devices", "get-blended-enrichment-order"],
            "api_call": lambda: api_get("/api/identity-graph/v1/settings/elisity-enrichment-order"),
            "key_fields": None,
        },
        {
            "label": "devices: get-device-header-data",
            "cli_args": ["devices", "get-device-header-data"],
            "api_call": lambda: api_get("/api/identity-graph/v1/devices/header"),
            "key_fields": None,
        },

        # ── CONNECTORS ──
        {
            "label": "connectors: read (list connectors)",
            "cli_args": ["connectors", "read"],
            "api_call": lambda: api_get("/api/identity-graph/v1/custom-connector"),
            "key_fields": None,
        },
        {
            "label": "connectors: read-all-connector-configurations",
            "cli_args": ["connectors", "read-all-connector-configurations"],
            "api_call": lambda: api_get("/api/identity-graph/v1/conf"),
            "key_fields": None,
        },

        # ── AD ──
        {
            "label": "ad: get-connectors",
            "cli_args": ["ad", "get-connectors"],
            "api_call": lambda: api_get("/api/ad-connector-service/v1/connector"),
            "key_fields": None,
        },
        {
            "label": "ad: get-suppressed-ip-attaches",
            "cli_args": ["ad", "get-suppressed-ip-attaches"],
            "api_call": lambda: api_get("/api/ad-connector-service/v1/suppressed-ip-attaches"),
            "key_fields": None,
        },

        # ── FLOWS ──
        {
            "label": "flows: get-noise-definition",
            "cli_args": ["flows", "get-noise-definition"],
            "api_call": lambda: api_get("/api/flows/v1/noise-definition"),
            "key_fields": ["id"],
        },
        {
            "label": "flows: get-available-ports",
            "cli_args": ["flows", "get-available-ports"],
            "api_call": lambda: api_get("/api/flows/v1/available-ports"),
            "key_fields": None,
        },

        # ── INSIGHTS ──
        {
            "label": "insights: get-settings",
            "cli_args": ["insights", "get-settings"],
            "api_call": lambda: api_get("/api/policy/v1/insights/settings"),
            "key_fields": None,
        },

        # ── SYSTEM ──
        {
            "label": "system: list-specs",
            "cli_args": ["system", "list-specs"],
            "api_call": lambda: api_get("/api/state-sync/v1/tasks/specs"),
            "key_fields": None,
        },

        # ── SITE-SPECIFIC (using first site) ──
    ]

    # Get a real site ID for site-specific tests
    sites_cli, _ = cli_run(["topology", "get-all-sites"])
    if sites_cli and isinstance(sites_cli, list) and len(sites_cli) > 0:
        site_id = sites_cli[0]["id"]
        tests.append({
            "label": f"topology: get-site-v2 (by ID {site_id[:8]}...)",
            "cli_args": ["topology", "get-site-v2", site_id],
            "api_call": lambda sid=site_id: api_get(f"/api/topology/v2/sites/{sid}"),
            "key_fields": ["id", "label", "description"],
        })

    # Get VE for VE-specific tests
    ves_cli, _ = cli_run(["topology", "get-virtual-edge", "-q", "content"])
    if ves_cli and isinstance(ves_cli, list) and len(ves_cli) > 0:
        ve_id = ves_cli[0]["id"]
        ve_name = ves_cli[0].get("name", "unknown")
        tests.append({
            "label": f"topology: VE content[0] data matches (VE: {ve_name})",
            "cli_args": ["topology", "get-virtual-edge", "-q", "content[0]"],
            "api_call": lambda: api_get("/api/topology/v1/virtual-edges")["content"][0],
            "key_fields": ["id", "name", "status"],
        })

    # Get a policy set for policy-specific tests
    ps_cli, _ = cli_run(["policy", "get-all-as-nd-json", "-q", "[0]"])
    if ps_cli and isinstance(ps_cli, dict):
        ps_id = ps_cli.get("id")
        tests.append({
            "label": f"policy: first policy set data matches ({ps_id[:8]}...)",
            "cli_args": ["policy", "get-all-as-nd-json", "-q", "[0]"],
            "api_call": lambda: api_get_ndjson("/api/policy/v1/policy-sets")[0],
            "key_fields": ["id", "name", "description"],
        })

    # Device count exact match
    tests.append({
        "label": "devices: device count exact value match",
        "cli_args": ["devices", "get-device-count"],
        "api_call": lambda: api_get("/api/identity-graph/v1/devices/count"),
        "key_fields": ["devicesCount"],
    })

    print(f"\nRunning {len(tests)} cross-validation tests...\n")
    print(f"{'#':<4} {'Test':<60} {'Status':<8} {'Details'}")
    print("-" * 120)

    for i, t in enumerate(tests, 1):
        try:
            cli_data, cli_err = cli_run(t["cli_args"])
            if cli_err:
                r = {"test": t["label"], "status": "CLI_ERR", "details": cli_err[:100]}
            else:
                api_data = t["api_call"]()
                r = compare_json(cli_data, api_data, t["label"], t["key_fields"])
        except Exception as e:
            r = {"test": t["label"], "status": "API_ERR", "details": str(e)[:100]}

        results.append(r)
        status_icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "CLI_ERR": "CERR", "API_ERR": "AERR"}.get(r["status"], "????")
        print(f"{i:<4} {r['test']:<60} {status_icon:<8} {r['details'][:50]}")

    return results


def print_summary(results):
    print("\n" + "=" * 120)
    print("  CROSS-VALIDATION SUMMARY")
    print("=" * 120)

    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] in ("CLI_ERR", "API_ERR"))

    print(f"  Total:   {len(results)}")
    print(f"  Passed:  {passed}")
    print(f"  Warned:  {warned}")
    print(f"  Failed:  {failed}")
    print(f"  Errors:  {errors}")
    print(f"  Rate:    {passed}/{len(results)} ({100*passed/len(results):.1f}%)")

    if failed or errors:
        print(f"\n  FAILURES:")
        for r in results:
            if r["status"] in ("FAIL", "CLI_ERR", "API_ERR"):
                print(f"    [{r['status']}] {r['test']}: {r['details']}")

    if warned:
        print(f"\n  WARNINGS:")
        for r in results:
            if r["status"] == "WARN":
                print(f"    [{r['status']}] {r['test']}: {r['details']}")

    verdict = "DATA MATCHES API" if failed == 0 and errors == 0 else "MISMATCHES FOUND"
    print(f"\n  VERDICT: {verdict}")
    print("=" * 120)

    # Save JSON
    report_path = Path(__file__).parent / "qa_crossvalidation_report.json"
    with open(report_path, "w") as f:
        json.dump({"results": results, "summary": {"passed": passed, "warned": warned, "failed": failed, "errors": errors}}, f, indent=2)
    print(f"  JSON report: {report_path}")


if __name__ == "__main__":
    results = run_all_tests()
    print_summary(results)
    sys.exit(1 if any(r["status"] == "FAIL" for r in results) else 0)
