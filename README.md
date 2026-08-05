# Elisity CCC CLI

[![tests](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml/badge.svg)](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml)

Command-line interface to the Elisity Cloud Control Center (CCC) API. Provides complete coverage of the CCC API surface — all 436 REST endpoints from the OpenAPI spec, plus 20 hand-coded GraphQL commands for the `/api/reporting/v1/data` endpoint (Zero Trust scores, threat vectors, per-site KPIs, traffic vectors) that the OpenAPI spec doesn't include, plus a 3-command CLI-native `glossary` group that maps Elisity UI terminology to CLI commands.

> **For AI agents:** see [docs/AGENTS.md](docs/AGENTS.md) for a UI-term → CLI-command operating guide. The `elisity glossary` group is the runtime lookup surface.

## Features

- **466 commands** total (436 auto-generated from the CCC OpenAPI spec + 20 hand-coded GraphQL reporting commands + 7 CLI-native auth/config + 3 CLI-native glossary commands)
- **Multi-profile configuration** — manage multiple CCC environments (prod, staging, lab)
- **4 output formats** — JSON (default), table, YAML, CSV
- **JMESPath filtering** — reshape and filter output with `-q` expressions
- **OAuth2 authentication** — client_credentials grant with auto-refresh
- **NDJSON support** — transparent parsing of newline-delimited JSON endpoints
- **GraphQL reporting** — `reporting` group wraps the CCC dashboard's GraphQL queries (Zero Trust scores, site KPIs, threat vectors, traffic-by-PG/IP)
- **UI-term glossary** — `glossary` group answers "what command runs the Zero Trust Score tile?" without guesswork
- **Destructive-op safety** — DELETE commands require `--confirm`
- **Retry with backoff** — automatic retry on connection errors and timeouts

## Quick Start

```bash
# Clone
git clone https://github.com/mkorenbaum/elisity-cli.git
cd elisity-cli

# Install (use a venv — modern Ubuntu/Debian block system-wide pip per PEP 668)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure
elisity config set-profile myenv \
  --base-url https://your-ccc.idp01.elisity.io \
  --client-id YOUR_CLIENT_ID \
  --client-secret 'YOUR_CLIENT_SECRET'

# Verify
elisity auth test

# What command runs the "Zero Trust Score" tile in the UI?
elisity glossary explain "Zero Trust score"
```

**Or use environment variables:**

```bash
export CCC_BASE_URL=https://your-ccc.idp01.elisity.io
export CCC_CLIENT_ID=your-client-id
export CCC_CLIENT_SECRET='your-client-secret'
elisity auth test
```

> **For agents and humans new to Elisity:** read **[docs/user-guide.md](docs/user-guide.md)** before doing real work. It is the workflow-oriented guide and has worked examples for the most common queries (devices per site, VEN inventory, posture score, flow search, scripting). The README below is reference material; the user guide is the tutorial. AI agents should additionally read [docs/AGENTS.md](docs/AGENTS.md).

## Usage

```bash
# List sites
elisity topology get-all-sites

# List sites as a table
elisity -f table topology get-all-sites

# Extract just site names
elisity topology get-all-sites -q '[].name'

# View devices (paginated — note nested 'pageable' wrapper)
elisity devices get-devices-view --body '{"pageable":{"page":0,"size":10}}'

# List policy sets
elisity policy get-all-as-nd-json

# Get a specific site by ID
elisity topology get-site-v2 <SITE_ID>

# Delete a site (requires confirmation)
elisity topology delete-site-v2 <SITE_ID> --confirm

# Tenant Zero Trust score (GraphQL reporting endpoint, not in OpenAPI spec)
elisity reporting get-aggregate-enforcement-score

# Per-site KPI dashboard (devices, VENs, policy counts, enforcement score)
elisity -f table reporting get-site-kpis

# Map UI term → CLI command
elisity glossary search "monitor mode"
elisity glossary explain "VEN"

# Get bearer token for use in scripts
TOKEN=$(elisity auth token)
curl -H "Authorization: Bearer $TOKEN" https://your-ccc.idp01.elisity.io/api/topology/v2/sites
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| `topology` | 117 | Sites, distribution zones, VE groups, VEs, VENs, flow exporters, cloud controllers |
| `policy` | 117 | Policy sets, policies, policy groups, security profiles, site labels |
| `devices` | 59 | Device CRUD, bulk operations, enrichment, suppression, custom attributes |
| `ad` | 61 | Active Directory / Entra ID connectors, users, groups, agents |
| `connectors` | 22 | Custom connector configurations, import/export, connectivity |
| `insights` | 30 | Policy suggestions, dynamic/network group recommendations |
| `flows` | 18 | Traffic flow search, device state, noise definitions |
| `system` | 12 | Tasks, specs, state sync |
| `reporting` | 20 | **GraphQL** — Zero Trust scores, site KPIs, threat vectors, traffic-by-PG/IP. Hand-coded (the CCC reporting API is GraphQL, not in OpenAPI). |
| `glossary` | 3 | Map Elisity UI terminology to CLI commands |
| `auth` | 3 | Test connection, get token, decode JWT |
| `config` | 4 | Profile management, configuration display |

**Explore any group:**

```bash
elisity --help                    # All groups
elisity topology --help           # All topology commands
elisity topology get-site-v2 --help  # Command-specific help
elisity glossary list             # All glossary terms
```

## Output Formats

```bash
elisity topology get-all-sites                    # JSON (default)
elisity -f table topology get-all-sites           # Rich terminal table
elisity -f yaml topology get-all-sites            # YAML
elisity -f csv topology get-all-sites             # CSV with headers
```

## JMESPath Queries

```bash
# Site names only
elisity topology get-all-sites -q '[].name'

# Count items
elisity topology get-all-sites -q 'length(@)'

# Filter by field
elisity topology get-virtual-edge -q 'content[?status==`ACTIVE`]'

# Select specific fields
elisity topology get-all-sites -q '[].{name: name, id: id}'

# First 3 results
elisity topology get-all-sites -q '[0:3]'
```

## Multi-Environment Profiles

```bash
# Create profiles for different environments
elisity config set-profile prod --base-url https://prod.idp01.elisity.io --client-id ID --client-secret SECRET
elisity config set-profile lab  --base-url https://lab.idp01.elisity.io  --client-id ID --client-secret SECRET

# Switch between them
elisity config use-profile prod
elisity config use-profile lab

# Or use -p flag for one-off commands
elisity -p lab topology get-all-sites

# List all profiles
elisity config list-profiles

# Show active config (secrets redacted)
elisity config show
```

## Requirements

- Python 3.10+
- Network access to a CCC instance
- OAuth2 service account credentials (client ID + secret)

## Dependencies

- [Click](https://click.palletsprojects.com/) — CLI framework
- [Requests](https://requests.readthedocs.io/) — HTTP client
- [Tenacity](https://tenacity.readthedocs.io/) — Retry logic
- [Rich](https://rich.readthedocs.io/) — Terminal table rendering
- [PyYAML](https://pyyaml.org/) — YAML output and config parsing
- [JMESPath](https://jmespath.org/) — Query language for JSON

## Development

```bash
# Clone and install in dev mode
git clone <repo-url>
cd elisity-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run QA validation against a live CCC
python3 tests/qa_comprehensive.py
```

### Regenerating commands from a new CCC OpenAPI spec

The API-backed groups are generated from the CCC OpenAPI specification, pulled from a
live tenant at `GET /v3/api-docs`. The current command set was generated from the CCC
26.3-era spec (`info.version` 1.0.0, 329 paths / 436 operations, captured 2026-06-21).

**Always diff before you regenerate.** The diff is what makes a version bump reviewable:

```bash
# 1. What changed between the two specs?
python3 tools/spec_diff.py old-api-docs.json new-api-docs.json

# Machine-readable form, and a mode that fails when a new tag has no group mapping
python3 tools/spec_diff.py old-api-docs.json new-api-docs.json --json > diff.json
python3 tools/spec_diff.py old-api-docs.json new-api-docs.json --strict
```

`spec_diff.py` reports added, removed and changed operations — including parameter
type/required changes, request-body and response schema changes (resolved through
`$ref`, so a change *inside* a referenced schema is visible), and the CLI command each
operation becomes. New tags with no `TAG_TO_GROUP` entry are surfaced separately: they
fall back to a path-prefix guess and need an explicit mapping decision.

```bash
# 2. Map any new tags in TAG_TO_GROUP (generate_commands.py), then regenerate.
python3 generate_commands.py --spec new-api-docs.json

# The spec path resolves as: --spec > $ELISITY_API_SPEC > the historical host path
ELISITY_API_SPEC=new-api-docs.json python3 generate_commands.py

# 3. Confirm counts, the delete gate, and the docs all still agree.
python3 tools/audit_counts.py
pytest
```

`audit_counts.py` walks the source tree and emits the authoritative numbers — total,
per group, generated vs hand-coded, delete commands and `--confirm` coverage. It exits
non-zero when `README.md` or `docs/command-reference.md` disagree with the source, so
documentation drift fails CI instead of accumulating. It is also enforced from the test
suite (`tests/test_command_invariants.py`).

Two invariants are enforced mechanically because a bulk regeneration is too large to
review by eye:

- **Delete gate** — every command issuing `client.delete()` requires `--confirm`.
  Coverage is asserted at 100%; a regression names the offending commands.
- **Hand-coded survival** — the `reporting` (GraphQL) and `glossary` (CLI-native) groups
  are not in the OpenAPI spec. Regeneration never rewrites their modules and always
  keeps them registered in `COMMAND_GROUPS`; the generator aborts if a spec tag is ever
  mapped onto one of them.

## Documentation

- [Getting Started](docs/getting-started.md) — First-time setup walkthrough
- [User Guide](docs/user-guide.md) — Workflow-oriented guide with real examples
- [AI Agent Operating Guide](docs/AGENTS.md) — How an AI agent should run the CLI on a human's behalf
- [Glossary Appendix](docs/glossary.md) — UI term → CLI command reference (human-readable)
- [Configuration Reference](docs/configuration.md) — Profiles, env vars, output formats, JMESPath
- [Command Reference](docs/command-reference.md) — All 466 commands with descriptions

## License

Proprietary - Elisity, Inc.
