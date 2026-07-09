# Elisity CCC CLI

[![tests](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml/badge.svg)](https://github.com/mkorenbaum/elisity-cli/actions/workflows/test.yml)

Command-line interface to the Elisity Cloud Control Center (CCC) API. Provides complete coverage of the CCC API surface — all 436 REST endpoints from the OpenAPI spec, plus 19 hand-coded GraphQL commands for the `/api/reporting/v1/data` endpoint (Zero Trust scores, threat vectors, per-site KPIs, traffic vectors) that the OpenAPI spec doesn't include, plus a 3-command CLI-native `glossary` group that maps Elisity UI terminology to CLI commands.

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
| `reporting` | 19 | **GraphQL** — Zero Trust scores, site KPIs, threat vectors, traffic-by-PG/IP. Hand-coded (the CCC reporting API is GraphQL, not in OpenAPI). |
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

- Python 3.9+
- Network access to a CCC instance
- OAuth2 service account credentials (client ID + secret)

> **You are on the `compat/python-3.9` branch. Use it only where Python 3.9 is mandatory.**
> Every other environment should use `main`.
>
> This branch holds `requests` at its terminal 3.9-compatible release, and on Python 3.9 holds
> `urllib3` there too. Those releases carry three unfixed CVEs that `main` does not have, and
> on 3.9 this branch can never receive the fixes — see [Security](#security). Running it where
> 3.9 is not a hard requirement means accepting a less secure dependency stack for no benefit.
>
> `src/` and `tests/` are byte-identical to `main`. The dependency pins, the CI matrix, and
> these docs are what differ; the downgraded pins sit at the newest releases that still
> support 3.9. This branch is maintained in parallel and is never merged into `main`.
>
> **The only interpreter exercised while preparing this branch was Python 3.12.** The CI
> matrix covers 3.9, 3.10, 3.11 and 3.12 and is the authority; treat support for the other
> three as unproven until it has run green.
>
> `main` targets **Python 3.10+** and tracks current dependency versions.

## Security

This branch exists to support Python 3.9. That carries an unavoidable cost, stated here in
full so you can take it knowingly.

### Known unfixed CVEs on this branch

Supporting 3.9 requires pinning the terminal 3.9-compatible releases of two packages —
`requests==2.32.5` on every interpreter, and `urllib3==2.6.3` on Python 3.9. Both carry
published CVEs:

| Package | Version | CVE | Severity | Applies on | Issue |
|---|---|---|---|---|---|
| `urllib3` | 2.6.3 | CVE-2026-44431 | HIGH | **Python 3.9 only** | `Authorization` / `Cookie` headers forwarded across origins on low-level proxied redirects |
| `urllib3` | 2.6.3 | CVE-2026-44432 | HIGH | **Python 3.9 only** | Decompression-bomb safeguards bypassed in the streaming API |
| `requests` | 2.32.5 | CVE-2026-25645 | MODERATE | every interpreter | Insecure temp-file reuse in `extract_zipped_paths()` |

**On Python 3.9 these will never be fixed.** The fixes ship in `urllib3` 2.7.0 and `requests`
2.33.0. Both of those releases declare `requires-python >= 3.10` — each upstream dropped 3.9
in the same release that carried the fix. No 3.9-compatible fixed version exists, and none is
coming. `main` installs `urllib3` 2.7.0 and `requests` 2.33.1 and is unaffected.

On Python 3.10+ this branch installs the patched `urllib3` 2.7.0 (see below), so only the
`requests` advisory applies there. That narrows the gap; it does not close it, and it is not a
reason to run this branch on 3.10+.

Downgrading further makes it worse, not better. `urllib3` 2.5.0 also resolves on 3.9 and
predates CVE-2026-44432, but carries four HIGH CVEs of its own, three of which 2.6.3 fixes.
2.6.3 is the minimum-exposure choice available to Python 3.9.

### Why `urllib3` is constrained explicitly

`urllib3` is only a transitive dependency of `requests`, and `requests` merely bounds it to
`urllib3<3,>=1.21.1`. Left to float, the branch had no control over the most
security-sensitive component in its tree: any future pip resolution could change its transport
behavior silently, and a later urllib3 that still supported 3.9 could regress it unnoticed.

`pyproject.toml` therefore constrains it directly, with an environment marker rather than a
single flat pin:

```toml
"urllib3==2.6.3; python_version < '3.10'",
"urllib3>=2.7.0,<3; python_version >= '3.10'",
```

The marker is load-bearing. A flat `urllib3==2.6.3` would have forced the vulnerable transport
onto 3.10+ installs of this branch, which otherwise resolve the patched 2.7.0 — trading a real
security regression for uniformity nobody asked for. The split holds Python 3.9 at its
terminal release, where there is no alternative, and lets every newer interpreter take the
fix. Exactly one of the two constraints is active on any given interpreter, and both satisfy
`requests`' own `urllib3<3,>=1.21.1` bound.

### Why none of the three is reachable through this CLI

Each was checked against this CLI's real code paths, by reproduction rather than by reading
the advisory text:

- **CVE-2026-44431 (headers on cross-origin redirect).** The flaw lives in urllib3's
  *low-level* `ProxyManager.connection_from_url().urlopen(..., assert_same_host=False)` path.
  This CLI only ever uses `requests.Session`, which calls `conn.urlopen(..., redirect=False)`
  and follows redirects itself, stripping `Authorization` and `Cookie` on host change via
  `Session.rebuild_auth`. Driving a live cross-origin 302 against the real 3.9 stack leaked
  the bearer token on the low-level path — reproducing the CVE — and leaked nothing on the
  high-level path this CLI actually uses.
- **CVE-2026-44432 (decompression bomb).** Two triggers, both closed here. The brotli trigger
  requires the `brotli` or `brotlicffi` package, which is absent from this CLI's dependency
  closure; without it urllib3 advertises only `Accept-Encoding: gzip,deflate`. The
  `drain_conn()` trigger is never reached: `requests` never calls `drain_conn()`, and
  urllib3's own call sites are gated behind `redirect=True` or an active retry policy, and
  `requests` uses neither.
- **CVE-2026-25645 (temp-file reuse).** `requests` does call `extract_zipped_paths()`
  internally on every HTTPS request, but the function returns the CA-bundle path unchanged
  when that path exists on disk — which it does under any normal `pip` or venv install. The
  vulnerable extraction branch requires `requests` or `certifi` to live *inside a zip archive*
  (zipapp, `.egg`, py2exe) **and** a local attacker with write access to `TMPDIR`.

Unreachable is not the same as absent. A vulnerability scanner pointed at this branch will
report all three, and it will be right to.

### The condition to watch

**On Python 3.9, do not install `brotli` or `brotlicffi` into the same environment as this
CLI.** With either present, urllib3 advertises `br` in `Accept-Encoding` and enables its real
brotli decoder, and `requests.iter_content()` already performs the chunked multi-read that
CVE-2026-44432 needs. A CCC endpoint returning `Content-Encoding: br` would then bring the
decompression-bomb path into scope. Absent brotli, that precondition cannot be met. This is
the one residual condition that turns an unreachable HIGH into a reachable one, and it is
reachable purely by installing an unrelated package alongside the CLI.

On Python 3.10+ the patched urllib3 2.7.0 removes this concern.

Two further conditions would extend exposure, and this CLI meets neither: packaging it as a
zipapp, `.egg`, or py2exe bundle makes CVE-2026-25645 live; calling urllib3's low-level
`ProxyManager` API directly makes CVE-2026-44431 live.

### If you do not need Python 3.9

Use `main`. It receives the dependency security fixes this branch structurally cannot.

## Known differences from main

`src/` and `tests/` are byte-identical to `main`, but one observable behavior still differs,
because the pinned `click` version differs (8.1.8 here, 8.3.1 on `main`):

**Invoking a command group with no subcommand exits `0` on this branch and `2` on `main`.**

```bash
elisity policy ; echo $?     # 0 on this branch, 2 on main
```

This affects the root command and all 12 groups — `auth`, `config`, `ad`, `connectors`,
`devices`, `flows`, `glossary`, `insights`, `policy`, `reporting`, `system`, `topology` — 13
invocations in total. The help text printed to stdout is byte-identical in both cases; only
the exit code differs, so neither the test suite nor a help-tree walk detects it.

If you script `elisity policy || die`, or otherwise branch on the exit status of a bare group
invocation, it will behave differently depending on which branch is installed. Branch on the
exit status of the subcommand you actually intend to run. This is deliberately not corrected
here, because `src/` is held byte-identical to `main`.

## Dependencies

- [Click](https://click.palletsprojects.com/) — CLI framework
- [Requests](https://requests.readthedocs.io/) — HTTP client
- [urllib3](https://urllib3.readthedocs.io/) — HTTP transport under Requests; constrained
  explicitly on this branch rather than left to float (see [Security](#security))
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
- [AI Agent Operating Guide](docs/AGENTS.md) — How an AI agent should run the CLI on a human's behalf
- [Glossary Appendix](docs/glossary.md) — UI term → CLI command reference (human-readable)
- [Configuration Reference](docs/configuration.md) — Profiles, env vars, output formats, JMESPath
- [Command Reference](docs/command-reference.md) — All 466 commands with descriptions

## License

Proprietary - Elisity, Inc.
