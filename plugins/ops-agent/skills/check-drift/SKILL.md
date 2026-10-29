---
name: check-drift
description: Compare what is running with what the repos say, using terraform plan and Argo CD sync status, then explain each difference and fix it by PR. Use on a schedule or when a drift alert fires.
---

# Check for drift

Status: phase 1 outline. Written out and tested in phase 6.

1. Run `terraform plan` for each stack, and read the Argo CD sync status of every application
   with `claude-ro`.
2. For each difference, find the cause: a change made by hand, a controller that edits objects,
   or a change that merged but never applied.
3. Fix it in the repo by PR, or add an ignore rule with the reason when the difference is
   expected.
4. Post a summary on the drift issue.

Done when: every stack plans clean and every application is synced, or each exception is
written down.
