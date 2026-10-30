# toil-lab agents

Two Claude Code plugins that work in tandem the way a developer and a DevOps engineer do on a
real team:

- `dev-agent` writes application code, tests, the Dockerfile, and `service.yaml`, the spec of
  what a service needs to run.
- `ops-agent` runs the Kubernetes platform, turns each `service.yaml` into a deployment, reviews
  every change to one, and handles upgrades, drift, CVEs, incidents, and cost checks.

Each agent runs as its own Claude Code session in its own repo. They share no context and talk
only through GitHub issues, pull requests, and reviews, so every handoff is written down. A human
approves every merge.

Status: phase 1. The guard hooks, the service contract, and the agent definitions are written
and tested. The skills are outlines that later phases write out and test against a live
platform.

## What's in the plugins

| | dev-agent | ops-agent |
|---|---|---|
| Main agent | `developer` | `operator` |
| Reviewer subagent | `code-reviewer` | `platform-reviewer` |
| Skills | build-feature, fix-bug, answer-ops-review, update-app-dependencies | onboard-team, onboard-service, review-service-spec, upgrade-platform, triage-cve, triage-alert, check-drift, write-postmortem, cost-check |
| Guard hooks | scope, kube context, identity, host load | scope, kube context, identity, host load, GCP spend |
| GitHub identity | `toil-dev-bot` App, through `toil-gh` and `toil-git` | `toil-ops-bot` App, through `toil-gh` and `toil-git` |

## Guard hooks

The guards are PreToolUse hooks. They stop mistakes before they happen; RBAC on the cluster
contexts, CODEOWNERS, and branch protection are the actual security boundary.

| Guard | Does | Decision |
|---|---|---|
| `scope_guard.py` | Keeps each agent inside its own files, using the repo's `toil.json` | deny |
| `kube_context_guard.py` | Requires a `claude-*` context on every `kubectl` and `helm` call that reaches the cluster; the developer agent gets read-only `claude-<team>-logs` contexts | deny |
| `identity_guard.py` | Refuses plain `gh`, and `git` commit, push, pull, merge, and rebase, which would act as the human; the agent uses `toil-gh` and `toil-git` | deny |
| `host_load_guard.py` | Stops cluster creation, image builds, installs, applies, and load tests for approval on a shared machine; `TOIL_HOST_SHARED=0` turns it off | ask |
| `gcp_spend_guard.py` | Stops anything that could create billable Google Cloud resources for approval | ask |

Who may edit what, by repo kind:

| Role | app repo | platform repo | agents repo |
|---|---|---|---|
| dev | everything except `.github/` and `CODEOWNERS` | nothing | everything except `hooks/` and `bin/` |
| ops | only `.github/` and `CODEOWNERS` | everything | everything except `hooks/` and `bin/` |

No agent edits `toil.json`.

## GitHub identity

Each agent acts on GitHub as its own GitHub App, so its issues, PRs, reviews, and commits show
up under a bot account, and only a human's approval satisfies the branch rulesets. Each plugin's
`bin/` folder is on the Bash tool's PATH and holds two commands:

- `toil-gh` runs `gh` with a short-lived installation token for the plugin's App.
- `toil-git` runs `git` with the App's bot name and email and a credential helper that supplies
  the same token for github.com.

Both call `bin/toil_app.py`, which signs a JWT with the App's private key through the `openssl`
command, exchanges it for an installation token, and caches the token in `~/.toil/cache/` until
10 minutes before it expires. The token is never printed. Setup, once per machine:

1. Create one GitHub App per agent in the organization's settings, and install each on the
   organization. The developer agent's App gets no Workflows permission, so GitHub itself
   refuses any push from it that changes `.github/workflows/`.
2. Save each App's private key outside every repo, for example `~/.toil/keys/`.
3. Write `~/.toil/apps.json` (the format is at the top of `toil_app.py`), then check each role:

   ```
   python plugins/dev-agent/bin/toil_app.py check --role dev
   ```

## The service contract

`contract/service.schema.json` (version 1) defines `service.yaml`. The developer agent writes
it, CI validates it with `contract/validate.py`, and the DevOps agent reviews every change.
`contract/examples/` holds the specs for statuspage, the uptime monitor the lab builds.

```yaml
schema_version: 1
name: probe-worker
team: checks
kind: deployment
image: ghcr.io/toil-lab/probe-worker
port: 9090
health: { liveness: /healthz, readiness: /readyz }
resources: { cpu: 50m, memory: 32Mi }
scaling: { min: 1, max: 6, metric: queue, source: redis-stream/probes, target: 20 }
config: [PROBE_TIMEOUT]
secrets: [REDIS_URL]
depends_on: [checks-redis]
egress: [any-http]
```

## Using the plugins in a repo

1. Add `toil.json` at the repo root: `{"kind": "app", "team": "checks"}` for an app repo,
   `{"kind": "platform"}` for the platform repo.
2. Add the marketplace and install the plugin for that repo's role:

   ```
   claude plugin marketplace add <path or GitHub repo>
   claude plugin install dev-agent@toil-lab     # app repos
   claude plugin install ops-agent@toil-lab     # the platform repo
   ```

3. To make the session itself the agent, set `"agent": "dev-agent:developer"` or
   `"agent": "ops-agent:operator"` in the repo's `.claude/settings.json`.

Requirements: Python 3.8 or later, `sh` (Git Bash on Windows), and `openssl` (Git for Windows
includes it). The hooks and `toil_app.py` use only the Python standard library. `contract/validate.py` also needs `pyyaml` and `jsonschema`.

## Working on this repo

The guards, the App helper, and the contract are edited in `shared/hooks/`, `shared/bin/`, and
`contract/`, then copied into each plugin, because an installed plugin can't read files outside
its own folder. The `toil-gh` and `toil-git` shims are per plugin, because each fixes its role:

```
python scripts/sync_shared.py          # copy into plugins/
python -m unittest discover -s tests   # guard, App helper, contract, and sync tests
```

Agents don't edit the guard hooks that limit them or the App helper that sets their identity;
the scope guard refuses it. Change those in a session that doesn't have these plugins installed.

## License

MIT
