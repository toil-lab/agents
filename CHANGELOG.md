# Changelog

Each entry names the correction or decision that caused it.

## 0.1.0 (unreleased)

Phase 2 workspace.

- Each agent acts on GitHub as its own GitHub App (`toil-dev-bot`, `toil-ops-bot`) through
  `toil-gh` and `toil-git` in its plugin's `bin/`. `shared/bin/toil_app.py` mints and caches
  installation tokens without printing them. Decided because a single human login can't
  approve its own PRs, and an agent using that login could approve as the human.
- `identity_guard.py` refuses plain `gh` and identity-bearing `git` commands in agent sessions.
- The scope guard now also protects `shared/bin/` and `plugins/*/bin/`.
- `test` workflow runs the tests and the sync check on Python 3.12, and the guard and sync
  tests on Python 3.8, the oldest version the hooks support. Both are required checks.
- `CODEOWNERS` names the platform team for the whole repo.

Phase 1 skeleton.

- `dev-agent` and `ops-agent` plugins with main agents, reviewer subagents, and skill outlines.
- Guard hooks: scope, kube context, host load, and GCP spend, with tests. The GCP spend guard
  started as a user-level hook after the project owner asked for approval before any Google
  Cloud spending.
- `service.schema.json` version 1 and `validate.py`, with the statuspage service specs as
  examples.
- `toil.json` marks each repo's kind (app, platform, agents) for the scope guard. It is JSON
  so the hooks can read it with the standard library alone.
- Shared files are copied into each plugin by `scripts/sync_shared.py`, because installed
  plugins can't read files outside their own folder.
