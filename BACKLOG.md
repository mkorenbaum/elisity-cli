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
