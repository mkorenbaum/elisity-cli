"""Command groups.

Most groups are auto-generated from the CCC OpenAPI spec by
`generate_commands.py`. `reporting` is hand-coded because the CCC reporting
API at /api/reporting/v1/data is GraphQL and isn't in the OpenAPI spec.
`glossary` is hand-coded — it's a CLI-native group (no remote API surface)
that maps Elisity UI terminology to CLI commands.
"""

COMMAND_GROUPS = [
    "ad",
    "connectors",
    "devices",
    "flows",
    "glossary",
    "insights",
    "policy",
    "reporting",
    "system",
    "topology",
]
