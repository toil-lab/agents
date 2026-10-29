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
| Guard hooks | scope, kube context, host load | scope, kube context, host load, GCP spend |

## Guard hooks

The guards are PreToolUse hooks. They stop mistakes before they happen; RBAC on the cluster
contexts, CODEOWNERS, and branch protection are the actual security boundary.

| Guard | Does | Decision |
|---|---|---|
| `scope_guard.py` | Keeps each agent inside its own files, using the repo's `toil.json` | deny |
| `kube_context_guard.py` | Requires a `claude-*` context on every `kubectl` and `helm` call that reaches the cluster; the developer agent gets read-only `claude-<team>-logs` contexts | deny |
| `host_load_guard.py` | Stops cluster creation, image builds, installs, applies, and load tests for approval on a shared machine; `TOIL_HOST_SHARED=0` turns it off | ask |
| `gcp_spend_guard.py` | Stops anything that could create billable Google Cloud resources for approval | ask |

Who may edit what, by repo kind:

| Role | app repo | platform repo | agents repo |
|---|---|---|---|
| dev | everything except `.github/` and `CODEOWNERS` | nothing | everything except the guard hooks |
| ops | only `.github/` and `CODEOWNERS` | everything | everything except the guard hooks |

No agent edits `toil.json`.

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

Requirements: Python 3.8 or later, and `sh` (Git Bash on Windows). The hooks use only the Python
standard library. `contract/validate.py` also needs `pyyaml` and `jsonschema`.

## Working on this repo

The guards and the contract are edited in `shared/hooks/` and `contract/`, then copied into each
plugin, because an installed plugin can't read files outside its own folder:

```
python scripts/sync_shared.py          # copy into plugins/
python -m unittest discover -s tests   # guard, contract, and sync tests
```

Agents don't edit the guard hooks that limit them; the scope guard refuses it. Change hooks in a
session that doesn't have these plugins installed.

## License

MIT
