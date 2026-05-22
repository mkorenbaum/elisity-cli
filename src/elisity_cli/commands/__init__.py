"""Command groups.

Most groups are auto-generated from the CCC OpenAPI spec by
`generate_commands.py`. `reporting` is hand-coded because the CCC reporting
API at /api/reporting/v1/data is GraphQL and isn't in the OpenAPI spec.
"""

COMMAND_GROUPS = [
    "ad",
    "connectors",
    "devices",
    "flows",
    "insights",
    "policy",
    "reporting",
    "system",
    "topology",
]
