---
name: write-postmortem
description: Write a blameless postmortem from an incident issue, its timeline, and the fix PRs, with the developer agent adding the code analysis. Use after an incident is resolved.
---

# Write a postmortem

Status: phase 1 outline. Written out and tested in phase 7.

Input: a resolved incident issue.

1. Build the timeline from the issue, the alerts, the deploy history, and the PRs, with times.
2. State the impact: what was down or slow, for how long, and how it was noticed.
3. State the root cause plainly. For a code cause, ask the developer agent on its fix PR for a
   two- or three-sentence explanation, and quote it.
4. List what went well, what didn't, and the action items. Each action item becomes an issue
   with an owner.
5. Write `docs/postmortems/<date>-<slug>.md` in the platform repo and open the PR.

Done when: the postmortem is merged and every action item is an issue.
