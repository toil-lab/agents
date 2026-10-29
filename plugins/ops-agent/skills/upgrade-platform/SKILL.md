---
name: upgrade-platform
description: Review and land Renovate upgrades of platform components (Argo CD, monitoring charts, Kyverno, KEDA, k3s, Terraform providers), reading release notes and planning rollback. Use when Renovate opens a PR in the platform repo.
---

# Upgrade a platform component

Status: phase 1 outline. Written out and tested in phase 6.

Input: a Renovate PR in the platform repo.

1. Read the release notes between the versions. List breaking changes, CRD changes, and
   deprecated values this repo uses.
2. Fix values and manifests on the Renovate branch until the chart renders.
3. Write the rollback. For CRD changes, say whether the old version can run against the new
   CRDs.
4. State the expected RAM change, if any.
5. Comment with the risk (low, medium, or high) and the reason.

Done when: the PR renders, the risk comment is posted, and after merge Argo CD reports healthy.
