# elisity-cli — Backlog

Parking lot for deferred work. Newest first. Status: `BACKLOG` → `IN PROGRESS` → `DONE`.

---

## BL-1 — GitHub Action: auto-triage issues & review PRs

**Status:** `BACKLOG` (parked 2026-05-28)

**Goal:** When an issue is reported, Claude analyzes it and either posts a comment
or opens a PR with a fix. When a PR is opened, Claude reviews it and comments.
Mike is notified, reviews the comments/PR, and **merges to main himself**.
No auto-merge — Mike stays the gate.

Built on the official [`anthropics/claude-code-action`](https://github.com/anthropics/claude-code-action).

### Decisions to make first (Mike picks, then the agent builds)

1. **Auth** — `CLAUDE_CODE_OAUTH_TOKEN` (via `claude setup-token`, uses Mike's
   Claude plan — *recommended*) **vs** `ANTHROPIC_API_KEY` (separate API billing).
2. **Trigger** — `@claude` mention only (*recommended*, lowest cost/noise) **vs**
   auto on every newly opened issue + PR.
3. **Notify** — Slack DM to Mike (needs `SLACK_BOT_TOKEN` repo secret) **vs**
   GitHub's native email/web notifications (zero extra setup).

### What Mike needs to do (manual — cannot be automated)

- [ ] **Install the Claude GitHub App** on `mkorenbaum/elisity-cli` — run
  `/install-github-app` from Claude Code, or install from
  <https://github.com/apps/claude> and grant access to this repo.
- [ ] **Generate the auth token** — `claude setup-token` (if using the OAuth path),
  copy the token.
- [ ] **Add the repo secret** — GitHub → repo **Settings → Secrets and variables →
  Actions → New repository secret**: name it `CLAUDE_CODE_OAUTH_TOKEN`
  (or `ANTHROPIC_API_KEY`). If Slack notify is chosen, also add `SLACK_BOT_TOKEN`.
- [ ] **Tell the agent the 3 decisions** above so it can wire the right triggers/secret.

### What the agent will code up

- [ ] Add `.github/workflows/claude.yml` using `anthropics/claude-code-action@v1`
  (repo already has `.github/workflows/test.yml` — leave it untouched).
- [ ] **Triggers** (per decision 2):
  - *Mention mode:* `issues` (opened), `issue_comment`, `pull_request`,
    `pull_request_review_comment` — gated on the body containing `@claude`.
  - *Auto mode:* `issues: [opened]` → analyze + comment or open a fix PR;
    `pull_request: [opened, synchronize]` → review + comment.
- [ ] **Permissions:** `contents: write`, `pull-requests: write`, `issues: write`,
  `id-token: write`.
- [ ] Pass the secret as the action input (`claude_code_oauth_token:` or
  `anthropic_api_key:`).
- [ ] (Optional) A second `claude-review.yml` dedicated to automatic PR review if
  auto mode is chosen, to keep issue-fix and PR-review prompts separate.
- [ ] **If Slack notify:** final workflow step posts to Mike's DM via
  `curl` + `SLACK_BOT_TOKEN` with the PR/comment URL. **xoxb bot token only**
  (per Obiwan Slack Token Policy — never the OAuth/user MCP path).
- [ ] **Guardrails:** never enable auto-merge; Claude opens PRs as draft/"For Review";
  destructive/state-changing changes stay human-approved.

### Verification

- [ ] Open a throwaway test issue (with `@claude` in mention mode); confirm Claude
  comments / opens a PR, and — if configured — the Slack ping arrives. Then close
  the test issue.

---

## BL-2: array and enum query parameters degrade to a single untyped string

**Source:** Leia round-1 QA, finding L-3. **Status:** open, needs a live-tenant
answer before any code is written.

`generate_commands.py` maps every parameter that is not `integer` or `boolean` to
`type=str, multiple=False`, and ignores `enum` entirely. Two consequences:

- **Arrays.** CCC 26.7 declares 6 query parameters as `"type": "array"` — `siteIds`
  on `/api/topology/v1/dashboard/count`, `source` (x2), `columnFilter` and `sort`
  on the two new `/api/reporting/v1/snapshot*` endpoints — against 4 in 26.3. The
  generated flag accepts exactly one value with no way to express a list.
- **Enums.** 45 enum-constrained query parameters in 26.7 (21 in 26.3) get no
  `click.Choice`, so a typo becomes a server-side error instead of a local one.

Pre-existing behaviour that 26.7 widens; not a regression.

**Why this is not fixed in the 26.7 round.** The array half cannot be settled
statically: whether CCC accepts `?siteIds=a,b` or requires `?siteIds=a&siteIds=b`
determines whether the fix is `multiple=True` (repeated keys) or a comma-joined
single value, and the two produce different HTTP requests. Guessing means
shipping a request shape nobody has seen the server accept — the same class of
error as re-pointing a metric at a field whose units are unknown.

**What would close it:**

1. Against a live 26.7 tenant, call `/api/topology/v1/dashboard/count` with
   `?siteIds=<a>&siteIds=<b>` and again with `?siteIds=<a>,<b>`. Record which
   returns data for both sites.
2. Implement the winning form for `"type": "array"` parameters — `multiple=True`
   for repeated keys, or an explicit comma-join for the other — and add a
   generated-command test that drives it through Click and asserts the wire shape.
3. Enums are independent of the above and safe to do either way: emit
   `click.Choice(...)` when the schema declares one. Worth confirming first that
   the spec's enum lists are complete for the params concerned, since a
   `click.Choice` built from a short list rejects values the API would accept.
