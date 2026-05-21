#!/usr/bin/env python3
"""
Patch generate_commands.py to enforce required query parameters.

Fix 1: When OpenAPI spec says required=True for a query param and there's no default,
generate Click option with required=True instead of default=None.

Usage:
    cd /home/elisity/Projects/elisity-cli
    python3 /path/to/fix-required-params-2026-04-07.py

This script:
1. Reads generate_commands.py
2. Patches the query param generation logic
3. Writes the patched file back
4. Verifies the patch with py_compile
"""

import re
import sys
import os
import py_compile
import shutil
from datetime import datetime

CLI_DIR = os.environ.get("ELISITY_CLI_DIR", "/home/elisity/Projects/elisity-cli")
GEN_FILE = os.path.join(CLI_DIR, "generate_commands.py")


def patch_generate_commands():
    if not os.path.exists(GEN_FILE):
        print(f"ERROR: {GEN_FILE} not found. Set ELISITY_CLI_DIR env var.", file=sys.stderr)
        sys.exit(1)

    # Backup original
    backup = f"{GEN_FILE}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(GEN_FILE, backup)
    print(f"Backup: {backup}")

    with open(GEN_FILE, "r") as f:
        content = f.read()
    lines = content.split("\n")

    # Find the query param generation block. We're looking for a pattern like:
    #   for pname, ptype, preq, pdesc, pdefault in query_params:
    # followed by lines that generate Click options with default=None
    #
    # The fix: when preq is True and pdefault is None, use required=True instead of default=None

    patched = False
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Pattern 1: Look for the query param loop that unpacks (pname, ptype, preq, pdesc, pdefault)
        # and the subsequent block that writes click options with default=None
        if "pname, ptype, preq, pdesc, pdefault" in line and "for " in line and "query_params" in line:
            new_lines.append(line)
            i += 1

            # Now scan forward through the loop body to find where default=None is written
            # and add required=True logic
            indent_found = False
            while i < len(lines):
                line = lines[i]

                # Look for the line that writes default=None for query params
                # Common patterns:
                #   f'    default=None,'
                #   f"    default=None,"
                #   lines.append(f'..., default=None, ...')
                #   or a block that constructs the click.option decorator

                if "default=None" in line and not patched:
                    # Replace this line with conditional logic
                    # Get the indentation
                    indent = len(line) - len(line.lstrip())
                    indent_str = line[:indent]

                    # Check if this is inside an f-string or a string concatenation
                    # We need to handle both cases

                    if "'default=None'" in line or '"default=None"' in line:
                        # It's a literal string being written - replace with conditional
                        old_default = line
                        # Replace the hardcoded default=None with a conditional
                        new_lines.append(f"{indent_str}# Fix: enforce required=True when spec says required and no default")
                        new_lines.append(f"{indent_str}if preq and pdefault is None:")
                        new_lines.append(f"{indent_str}    {line.strip().replace('default=None', 'required=True')}")
                        new_lines.append(f"{indent_str}else:")
                        new_lines.append(f"{indent_str}    {line.strip()}")
                        patched = True
                        i += 1
                        continue

                    elif "default=None" in line:
                        # Could be f-string or format string
                        old_default = line
                        new_lines.append(f"{indent_str}# Fix: enforce required=True when spec says required and no default")
                        new_lines.append(f"{indent_str}if preq and pdefault is None:")
                        new_lines.append(f"{indent_str}    {line.strip().replace('default=None', 'required=True')}")
                        new_lines.append(f"{indent_str}else:")
                        new_lines.append(f"{indent_str}    {line.strip()}")
                        patched = True
                        i += 1
                        continue

                new_lines.append(line)
                i += 1

                # If we've left the for loop body (dedented back), stop scanning
                if line.strip() and not line.startswith("    ") and not line.startswith("\t"):
                    break

            continue

        new_lines.append(line)
        i += 1

    if not patched:
        print("WARNING: Could not find the exact pattern to patch automatically.")
        print("Attempting alternative patch strategy...")
        patched = try_alternative_patch(lines, new_lines)

    if not patched:
        print("ERROR: Auto-patch failed. Apply manual patch (see below).", file=sys.stderr)
        print_manual_patch()
        sys.exit(1)

    # Write patched file
    with open(GEN_FILE, "w") as f:
        f.write("\n".join(new_lines))

    # Verify syntax
    try:
        py_compile.compile(GEN_FILE, doraise=True)
        print(f"PATCHED: {GEN_FILE} — syntax OK")
    except py_compile.PyCompileError as e:
        print(f"SYNTAX ERROR after patch: {e}", file=sys.stderr)
        print(f"Restoring from backup: {backup}", file=sys.stderr)
        shutil.copy2(backup, GEN_FILE)
        sys.exit(1)


def try_alternative_patch(original_lines, new_lines):
    """Try a sed-style replacement on known patterns."""
    content = "\n".join(original_lines)

    # Pattern: the line that writes the click option with default=None in the query param loop
    # Common in Click code generators:
    #   lines.append(f"@click.option('--{param_name}', default=None, help='{desc}')")
    # or:
    #   code += f"    default=None,\n"

    # Strategy: find all lines with 'default=None' that are inside blocks
    # that also reference pname/ptype/preq and replace them

    # More targeted: look for the exact pattern where pdefault is referenced nearby
    patterns = [
        # Pattern A: f-string with default=None in click.option
        (r"([ \t]+)(.*?f['\"].*?default=None.*?['\"].*)", "default=None", "required=True"),
        # Pattern B: string concat with default=None
        (r"([ \t]+)(.*?['\"].*?default=None.*?['\"].*)", "default=None", "required=True"),
    ]

    # Actually, let's do a smarter approach: find the function that processes query params
    # and inject a conditional at the right place
    new_lines.clear()

    for i, line in enumerate(original_lines):
        # Find lines that write default=None in the context of query param generation
        # Check if we're within ~10 lines of a line mentioning preq or query_params
        if "default=None" in line:
            # Check surrounding context
            context_start = max(0, i - 15)
            context_end = min(len(original_lines), i + 5)
            context = "\n".join(original_lines[context_start:context_end])

            if ("preq" in context or "query_param" in context.lower()) and "pdefault" in context:
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                new_lines.append(f"{indent_str}# Fix: enforce required=True when spec says required and no default")
                # Replace default=None with conditional
                default_line = line.rstrip()
                required_line = default_line.replace("default=None", "required=True")
                new_lines.append(f"{indent_str}if preq and pdefault is None:")
                new_lines.append(f"{indent_str}    {required_line.strip()}")
                new_lines.append(f"{indent_str}else:")
                new_lines.append(f"{indent_str}    {default_line.strip()}")
                return True
        new_lines.append(line)

    return False


def print_manual_patch():
    """Print the manual patch instructions."""
    print("""
=== MANUAL PATCH INSTRUCTIONS ===

In generate_commands.py, find the query param generation loop (around line 214-220).
It looks like:

    for pname, ptype, preq, pdesc, pdefault in query_params:
        ...
        lines.append(f"..., default=None, ...")
        ...

Replace the line that writes `default=None` with:

        # Fix: enforce required=True when spec says required and no default
        if preq and pdefault is None:
            <same line but with required=True instead of default=None>
        else:
            <original line with default=None>

This ensures Click validates required params before sending the API request.
""")


if __name__ == "__main__":
    patch_generate_commands()
