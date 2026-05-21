# Elisity CLI — Live Validation Procedure

Manual step-by-step validation against a live CCC instance.
Covers all 10 categories from the automated QA suite (106 tests).

## Prerequisites

```bash
# Install the CLI
pip install -e /home/elisity/Projects/elisity-cli --break-system-packages

# Verify it's on PATH
elisity --version
# Expected: elisity-cli, version 0.1.0
```

> **Note on regenerating commands:** the required-param fix is baked into
> `generate_commands.py`. `fix-required-params.py` is retained for historical
> reference only; do not run it as part of the regen workflow.

---

## Step 1: Configuration & Profile Management

```bash
# 1a. Show current config (secret should be redacted)
elisity config show

# 1b. List profiles (client_secret values must appear as "***")
elisity config list-profiles

# 1c. Set up a profile for your CCC
elisity config set-profile --name my-lab \
  --url https://<YOUR-CCC-FQDN> \
  --client-id <YOUR-CLIENT-ID> \
  --client-secret <YOUR-CLIENT-SECRET>

# 1d. Switch to it
elisity config use-profile my-lab

# 1e. Verify switch
elisity config show
# Confirm base_url points to your CCC
```

---

## Step 2: Authentication

```bash
# 2a. Health check
elisity auth test
# Expected: {"status": "UP", ...}

# 2b. Get a raw token
elisity auth token
# Expected: eyJ... (JWT string)

# 2c. Decode token claims
elisity auth whoami
# Expected: JSON with client_id, iss (should contain "elisity"), exp
```

---

## Step 3: Help & Command Discovery

```bash
# 3a. Root help — should show 10 command groups
elisity --help

# 3b. Spot-check a few groups
elisity topology --help
elisity policy --help
elisity devices --help

# 3c. Verify command count (should be 434+)
elisity topology --help 2>&1 | grep -c "^  "
elisity policy --help 2>&1 | grep -c "^  "
# topology ~116, policy ~116
```

---

## Step 4: Read Operations (one per command group)

```bash
# TOPOLOGY
elisity topology get-sites-v2
elisity topology get-distribution-zones
elisity topology get-virtual-edges
elisity topology get-virtual-edge-nodes
elisity topology get-flow-exporters

# POLICY
elisity policy get-all-as-nd-json
elisity policy get-all-policies-as-nd-json
elisity policy get-policy-groups-json
elisity policy get-security-profiles-as-nd-json

# DEVICES
elisity devices get-devices-count
elisity devices get-enrichment-order

# CONNECTORS
elisity connectors get-connectivity-status
elisity connectors get-all-connector-configs

# AD
elisity ad get-all-ad-connector-configs
elisity ad get-configuration-value --name "user.preemption.enabled"

# FLOWS
elisity flows get-noise-definitions
elisity flows get-available-ports

# INSIGHTS
elisity insights get-settings

# SYSTEM
elisity system get-all-task-specs
```

---

## Step 5: Output Formats

Pick any command that returns data (e.g., `topology get-sites-v2`):

```bash
# 5a. JSON (default)
elisity topology get-sites-v2

# 5b. Table
elisity topology get-sites-v2 -f table

# 5c. YAML
elisity topology get-sites-v2 -f yaml

# 5d. CSV
elisity topology get-sites-v2 -f csv
```

---

## Step 6: JMESPath Queries

```bash
# 6a. Extract labels only
elisity topology get-sites-v2 -q "[].label"

# 6b. Select specific fields
elisity topology get-sites-v2 -q "[].{name: label, id: id}"

# 6c. Array slice (first 2)
elisity topology get-sites-v2 -q "[0:2]"

# 6d. Nested content extraction (paginated endpoint)
elisity policy get-policy-groups-json -q "content[].name"

# 6e. Single value
elisity topology get-sites-v2 -q "[0].label"

# 6f. Length function
elisity topology get-sites-v2 -q "length([*])"

# 6g. Command-level -q flag
elisity devices get-devices-count -q "count"
```

---

## Step 7: NDJSON & Path Parameters

These commands use NDJSON streaming and path parameters (the fixed bugs):

```bash
# 7a. Get a policy set ID
PS_ID=$(elisity policy get-all-as-nd-json -q "[0].id" | tr -d '"')
echo "Policy Set ID: $PS_ID"

# 7b. Policies for that policy set (was C8.04 — previously crashed with traceback)
elisity policy get-all-policies-for-policy-set-as-nd-json "$PS_ID"

# 7c. Policy groups for that policy set (was C8.05 — same fix)
elisity policy get-policy-groups-assigned-to-policy-set "$PS_ID"

# 7d. Count of policies in set
elisity policy get-count-of-all-policies-for-policy-set "$PS_ID"
```

---

## Step 8: POST with --body and --body-file

```bash
# 8a. Inline JSON body
elisity devices get-devices-view --body '{"page":0,"size":2}'

# 8b. Body from file
echo '{"page":0,"size":2}' > /tmp/test-body.json
elisity devices get-devices-view --body-file /tmp/test-body.json
rm /tmp/test-body.json

# 8c. Policy IP lookup
elisity policy lookup-evaluation-endpoint --body '{"ip":"10.0.0.1"}'
```

---

## Step 9: CRUD Lifecycle (create, read, update, delete)

```bash
# 9a. CREATE a test site
SITE_ID=$(elisity topology create-site-post \
  --body '{"label":"CLI-Validation-Test","description":"Manual validation"}' \
  | tr -d '"')
echo "Created site: $SITE_ID"

# 9b. READ it back
elisity topology get-site-v2 "$SITE_ID"

# 9c. UPDATE it
elisity topology update-site "$SITE_ID" \
  --body "{\"id\":\"$SITE_ID\",\"label\":\"CLI-Validation-Test\",\"description\":\"Updated by validation\"}"

# 9d. VERIFY update persisted
elisity topology get-site-v2 "$SITE_ID" -q "description"
# Expected: "Updated by validation"

# 9e. DELETE without --confirm (should fail)
elisity topology delete-site-v2 "$SITE_ID"
# Expected: "Use --confirm to execute this destructive operation."

# 9f. DELETE with --confirm
elisity topology delete-site-v2 "$SITE_ID" --confirm

# 9g. VERIFY deletion (should return 404 error)
elisity topology get-site-v2 "$SITE_ID"
# Expected: Error: 404
```

---

## Step 10: Error Handling & Safety

```bash
# 10a. Invalid subcommand
elisity topology fake-command
# Expected: "No such command"

# 10b. Invalid JSON body
elisity devices get-devices-view --body 'not-json'
# Expected: JSON parse error

# 10c. Invalid format choice
elisity topology get-sites-v2 -f xml
# Expected: "Invalid value for '-f'"

# 10d. Nonexistent body-file
elisity devices get-devices-view --body-file /tmp/does-not-exist.json
# Expected: Path does not exist

# 10e. Nonexistent resource
elisity topology get-site-v2 "00000000-0000-0000-0000-000000000000"
# Expected: 404 error
```

---

## Step 11: Pagination

```bash
# 11a. VENs — verify pagination fields present
elisity topology get-virtual-edge-nodes -q "{total: totalElements, pages: totalPages, size: size}"

# 11b. Policy groups — paginated
elisity policy get-policy-groups-json -q "{total: totalElements, pages: totalPages}"
```

---

## Appendix: Command Regeneration

When the CCC OpenAPI spec changes, regenerate the auto-generated command modules:

```bash
cd /home/elisity/Projects/elisity-cli
python3 generate_commands.py
```

The required-param enforcement (`required=True` for spec-required query params with
no default) is baked into `generate_commands.py` itself. **Do not run
`fix-required-params.py`** — it is retained for historical reference only and is
a no-op against the current generator (the regex it targets no longer matches
because the generator uses f-string interpolation for `default=...`).

---

## Summary Checklist

| # | Area | Commands | Pass? |
|---|------|----------|-------|
| 1 | Config & Profiles | `config show/list/set/use` | |
| 2 | Authentication | `auth test/token/whoami` | |
| 3 | Help & Discovery | `--help` on root + groups | |
| 4 | Read Ops (8 groups) | GET across all command groups | |
| 5 | Output Formats | `-f json/table/yaml/csv` | |
| 6 | JMESPath Queries | `-q` with various expressions | |
| 7 | NDJSON + Path Params | Policy set sub-resources | |
| 8 | POST Body | `--body` and `--body-file` | |
| 9 | CRUD Lifecycle | Create → Read → Update → Delete site | |
| 10 | Error Handling | Invalid input, missing args, safety guards | |
| 11 | Pagination | Verify `totalElements`, `totalPages` | |
