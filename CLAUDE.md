# agents repo

This repo is the toil-lab plugin marketplace: `plugins/dev-agent` and `plugins/ops-agent`, plus
the guard hooks they share and the `service.yaml` contract.

- Edit guards in `shared/hooks/`, the App helper in `shared/bin/`, and the contract in
  `contract/`. Never edit the copies under `plugins/*/hooks/`, `plugins/*/bin/`, or
  `plugins/*/contract/` directly. The `toil-gh` and `toil-git` shims in each plugin's `bin/` are
  the exception: they are per plugin. After any change, run
  `python scripts/sync_shared.py`.
- Run `python -m unittest discover -s tests` before every commit. Every guard behavior has a
  test case in `tests/test_guards.py`; add one with each change.
- Hooks and `toil_app.py` use only the Python standard library and run on Python 3.8 or later, on Windows (Git
  Bash) and Linux.
- A guard that fails must fail open with exit code 1 and a message on stderr (`guardlib.run`
  does this). Never exit 2: deny with a JSON decision so the reason reaches the agent.
- Each `CHANGELOG.md` entry names the correction or PR that caused it.
- `toil.json` here is `{"kind": "agents"}`. Agent plugin sessions can't edit the guard hooks in
  this repo; that is deliberate.
