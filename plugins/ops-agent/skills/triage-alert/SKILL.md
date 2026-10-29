---
name: triage-alert
description: Diagnose an alert with read-only cluster access, mitigate if possible, and route the root cause to a platform PR or an app issue with evidence. Use when Alertmanager opens an incident issue.
---

# Triage an alert

Status: phase 1 outline. Written out and tested in phase 7.

Input: an incident issue opened by Alertmanager.

1. Post on the issue that you are on it, with the time.
2. Gather evidence with `claude-ro`: pod status, events, recent logs, the relevant metrics, and
   the last deploys in Argo CD history.
3. If users are affected and a safe mitigation exists (roll back the last deploy, scale up),
   apply it with the team's `claude-<team>-dev` context in dev, or by PR for staging. Write what
   you did on the issue.
4. Decide where the root cause is. For a platform cause, open a platform PR. For a code cause,
   open an issue in the app repo with the logs, metrics, and failing request attached.
5. Keep the issue's timeline current; write-postmortem builds from it.

Done when: the alert is resolved and the root-cause PR or issue is linked.
