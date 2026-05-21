#!/usr/bin/env python3
"""
Elisity CLI — CCC UI Screenshot Cross-Validation
==================================================
Logs into the CCC UI via Keycloak OIDC browser flow, navigates to key pages,
takes screenshots, and captures data from the UI to compare with CLI output.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

CCC_URL = os.environ.get("CCC_BASE_URL", "https://tme-26-3.idp01.elisity.io")
CCC_USER = os.environ.get("CCC_USER", "zerotme")
CCC_PASS = os.environ.get("CCC_PASS", "Elisity!23")
ELISITY = "elisity"


def cli_run(args, timeout=30):
    cmd = [ELISITY] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                      env={**os.environ, "COLUMNS": "200"})
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except:
        return r.stdout.strip()


async def main():
    from pyppeteer import launch

    print(f"Launching headless Chrome against {CCC_URL}")
    print(f"Screenshots will be saved to: {SCREENSHOT_DIR}\n")

    browser = await launch(
        executablePath="/usr/bin/google-chrome-stable",
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
        ],
        defaultViewport={"width": 1920, "height": 1080},
    )

    page = await browser.newPage()

    # ── Step 1: Login via Keycloak OIDC flow ─────────────────────
    print("[1] Navigating to CCC (triggers Keycloak redirect)...")
    await page.goto(CCC_URL, waitUntil="networkidle2", timeout=30000)
    await asyncio.sleep(2)
    await page.screenshot(path=str(SCREENSHOT_DIR / "01_login_page.png"))
    print(f"  URL: {page.url}")

    # Detect Keycloak login form
    print("[2] Filling login credentials...")
    try:
        # Wait for any username input
        username_sel = None
        for sel in ['input#username', 'input[name="username"]', 'input[type="text"]', 'input[type="email"]']:
            try:
                await page.waitForSelector(sel, timeout=3000)
                username_sel = sel
                break
            except:
                continue

        if username_sel:
            # Clear and type username
            await page.click(username_sel, clickCount=3)
            await page.type(username_sel, CCC_USER)

            # Find password field
            for sel in ['input#password', 'input[name="password"]', 'input[type="password"]']:
                try:
                    await page.waitForSelector(sel, timeout=2000)
                    await page.click(sel, clickCount=3)
                    await page.type(sel, CCC_PASS)
                    break
                except:
                    continue

            await page.screenshot(path=str(SCREENSHOT_DIR / "02_login_filled.png"))

            # Click login button
            for sel in ['input#kc-login', 'button#kc-login', 'input[type="submit"]',
                        'button[type="submit"]', 'button:has-text("LOG IN")', '.btn-primary']:
                try:
                    btn = await page.querySelector(sel)
                    if btn:
                        await btn.click()
                        break
                except:
                    continue

            # Wait for redirect back to CCC
            try:
                await page.waitForNavigation(waitUntil="networkidle2", timeout=15000)
            except:
                pass
            await asyncio.sleep(5)
        else:
            print("  Could not find login form")

    except Exception as e:
        print(f"  Login error: {e}")

    await page.screenshot(path=str(SCREENSHOT_DIR / "03_post_login.png"))
    current_url = page.url
    print(f"  Post-login URL: {current_url}")
    logged_in = "login" not in current_url.lower() and "auth" not in current_url.lower()

    if not logged_in:
        print("  WARNING: Login may have failed. Checking error message...")
        error_text = await page.evaluate('() => document.querySelector(".alert-error, .kc-feedback-text, .error-message")?.textContent || "none"')
        print(f"  Error: {error_text}")
        # Try once more — maybe there's a TOTP or second step
        await page.screenshot(path=str(SCREENSHOT_DIR / "03b_login_state.png"))

    # ── Navigate pages (even if not logged in, to show what we get) ──

    pages_to_visit = [
        ("dashboard",                "04_dashboard.png",            "Dashboard"),
        ("topology/sites",           "05_topology_sites.png",       "Sites"),
        ("topology/virtual-edges",   "06_topology_ves.png",         "Virtual Edges"),
        ("topology/virtual-edge-nodes", "07_topology_vens.png",     "VENs"),
        ("policy/policy-sets",       "08_policy_sets.png",          "Policy Sets"),
        ("policy/policy-groups",     "09_policy_groups.png",        "Policy Groups"),
        ("devices",                  "10_devices.png",              "Devices"),
        ("policy/security-profiles", "11_security_profiles.png",    "Security Profiles"),
        ("settings/connectors",      "12_connectors.png",           "Connectors"),
        ("topology/distribution-zones", "13_distribution_zones.png", "Distribution Zones"),
    ]

    # CLI data to compare
    cli_checks = {
        "Sites": lambda: cli_run(["topology", "get-all-sites", "-q", "[].label"]),
        "Virtual Edges": lambda: cli_run(["topology", "get-virtual-edge", "-q", "content[].name"]),
        "VENs": lambda: cli_run(["topology", "get-virtual-edge-nodes", "-q", "totalElements"]),
        "Policy Sets": lambda: cli_run(["policy", "get-all-as-nd-json", "-q", "[].name"]),
        "Policy Groups": lambda: cli_run(["policy", "get-policy-groups-json", "-q", "totalElements"]),
        "Devices": lambda: cli_run(["devices", "get-device-count"]),
        "Security Profiles": lambda: cli_run(["policy", "get-all-security-profiles-as-nd-json", "-q", "length(@)"]),
        "Distribution Zones": lambda: cli_run(["topology", "get-all-distribution-zones", "-q", "[].name"]),
    }

    for path, filename, label in pages_to_visit:
        n = filename.split("_")[0]
        print(f"\n[{n}] {label}...")
        try:
            await page.goto(f"{CCC_URL}/{path}", waitUntil="networkidle2", timeout=20000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"  Navigation error: {e}")
        await page.screenshot(path=str(SCREENSHOT_DIR / filename))

        if label in cli_checks:
            data = cli_checks[label]()
            if data is not None:
                print(f"  CLI {label}: {json.dumps(data)[:120]}")

    await browser.close()

    # ── Summary ────────────────────────────────────────────────────
    screenshots = sorted(SCREENSHOT_DIR.glob("*.png"))
    print(f"\n{'='*60}")
    print(f"  SCREENSHOTS CAPTURED: {len(screenshots)}")
    print(f"{'='*60}")
    for s in screenshots:
        size_kb = s.stat().st_size / 1024
        print(f"  {s.name} ({size_kb:.0f} KB)")
    print(f"\n  Location: {SCREENSHOT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
