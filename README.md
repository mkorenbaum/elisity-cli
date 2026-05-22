# Elisity CCC CLI

[![tests](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml/badge.svg)](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml)

Command-line interface to the Elisity Cloud Control Center (CCC) API. Provides complete coverage of all 436 CCC API endpoints across topology, policy, devices, connectors, AD/Entra integration, traffic flows, insights, and system operations.

## Features

- **443 commands** (436 auto-generated from the CCC OpenAPI specification + 7 CLI-native auth/config)
- **Multi-profile configuration** — manage multiple CCC environments (prod, staging, lab)
- **4 output formats** — JSON (default), table, YAML, CSV
- **JMESPath filtering** — reshape and filter output with `-q` expressions
- **OAuth2 authentication** — client_credentials grant with auto-refresh
- **NDJSON support** — transparent parsing of newline-delimited JSON endpoints
- **Destructive-op safety** — DELETE commands require `--confirm`
- **Retry with backoff** — automatic retry on connection errors and timeouts

## Quick Start

```bash
# Install
pip install -e .

# Configure
elisity config set-profile myenv \
  --base-url https://your-ccc.idp01.elisity.io \
  --client-id YOUR_CLIENT_ID \
  --client-secret 'YOUR_CLIENT_SECRET'

# Verify
elisity auth test
```

**Or use environment variables:**

```bash
export CCC_BASE_URL=https://your-ccc.idp01.elisity.io
export CCC_CLIENT_ID=your-client-id
export CCC_CLIENT_SECRET='your-client-secret'
elisity auth test
```

## Usage

```bash
# List sites
elisity topology get-all-sites

# List sites as a table
elisity topology get-all-sites -f table

# Extract just site names
elisity topology get-all-sites -q '[].name'

# View devices (paginated)
elisity devices get-devices-view --body '{"page":0,"size":10}'

# List policy sets
elisity policy get-all-as-nd-json

# Get a specific site by ID
elisity topology get-site-v2 <SITE_ID>

# Delete a site (requires confirmation)
elisity topology delete-site-v2 <SITE_ID> --confirm

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
| `auth` | 3 | Test connection, get token, decode JWT |
| `config` | 4 | Profile management, configuration display |

**Explore any group:**

```bash
elisity --help                    # All groups
elisity topology --help           # All topology commands
elisity topology get-site-v2 --help  # Command-specific help
```

## Output Formats

```bash
elisity topology get-all-sites                    # JSON (default)
elisity topology get-all-sites -f table           # Rich terminal table
elisity topology get-all-sites -f yaml            # YAML
elisity topology get-all-sites -f csv             # CSV with headers
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

## Documentation

- [Getting Started](docs/getting-started.md) — First-time setup walkthrough
- [User Guide](docs/user-guide.md) — Workflow-oriented guide with real examples
- [Configuration Reference](docs/configuration.md) — Profiles, env vars, output formats, JMESPath
- [Command Reference](docs/command-reference.md) — All 443 commands with descriptions

## License

Proprietary - Elisity, Inc.
