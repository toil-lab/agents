---
name: update-app-dependencies
description: Review and fix Renovate pull requests for Go modules and base images in an app repo, reading release notes for breaking changes. Use when Renovate opens a dependency PR in an app repo.
---

# Update application dependencies

Status: phase 1 outline. Written out and tested in phase 6.

Input: a Renovate PR in the current app repo.

1. Read the release notes between the old and new versions. List any breaking changes and
   whether this code uses the affected parts.
2. If CI fails, fix the code on the Renovate branch.
3. For a base image change, check that the new image still runs as non-root and still has what
   the service needs at runtime.
4. Comment on the PR with the risk (low, medium, or high), the reason, and what you changed.

Done when: CI is green and the risk comment is posted for the approver.
