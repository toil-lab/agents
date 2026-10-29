---
name: fix-bug
description: Fix a bug the DevOps agent traced to application code, starting from its issue with logs, metrics, and the failing request. Use when a bug issue from the DevOps agent lands in an app repo.
---

# Fix a bug from an incident

Status: phase 1 outline. Written out and tested in phase 7.

Input: a bug issue in the current app repo, usually filed by the DevOps agent during an
incident.

1. Read the evidence on the issue. Reproduce the failure in a test before changing code.
2. If the evidence points somewhere other than the code, say so on the issue with your
   reasoning and hand it back to the DevOps agent.
3. Fix the code until the new test passes. Check whether the same mistake exists elsewhere.
4. Open the PR through the build-feature steps. In the description, name the incident and
   explain the root cause in two or three sentences; the postmortem quotes it.

Done when: the fix is merged and the incident issue links to it.
