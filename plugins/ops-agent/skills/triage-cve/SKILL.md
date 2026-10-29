---
name: triage-cve
description: Rank Trivy findings from CI by whether the vulnerable code is used and exposed, then open platform patch PRs or app issues. Use when a Trivy scan reports high or critical findings.
---

# Triage CVEs

Status: phase 1 outline. Written out and tested in phase 6.

Input: Trivy results from CI for an image or for the cluster's components.

1. Group findings by package and fixed version.
2. For each group, decide whether the package is used at runtime, whether it is reachable from
   outside the cluster, and whether a fixed version exists.
3. For platform components, open a patch PR. For app images, open an issue in the app repo for
   the developer agent with the finding and the fixed version.
4. Record the findings left open and why, so the next scan doesn't triage them again.

Done when: every high and critical finding has a PR, an issue, or a written reason to wait.
