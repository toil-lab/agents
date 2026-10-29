---
name: review-service-spec
description: Review a change to a service.yaml in an app repo against quotas, network policy, admission policy, and cost, then approve or request changes with reasons. Use when a dev PR changes service.yaml.
---

# Review a service.yaml change

Status: phase 1 outline. Written out and tested in phase 4.

Input: a dev PR that changes `service.yaml`.

1. Diff the old and new spec.
2. Check each change:
   - `resources` and `scaling`: does the maximum fit the team's ResourceQuota?
   - `egress`: is the destination justified? `any-http` and `any-tcp` need a reason in the PR,
     and the platform may narrow them.
   - `depends_on`: does the target exist, and does its owner allow the caller?
   - `exposes`: is the host free, and is the path unique?
   - `backing`: storage size against the host's disk budget.
   - Kyverno policies the change would break.
3. Comment on each problem with the rule it breaks and what would pass. Approve as a reviewer
   only when nothing is left; the human approver still has to approve.
4. When you request changes, record a spec bounce in the Lesson field with the reason.

Done when: the review is posted and, if approved, onboard-service has a PR open.
