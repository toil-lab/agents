# Changelog

Each entry names the correction or decision that caused it.

## 0.1.0 (unreleased)

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
