---
name: answer-ops-review
description: Respond to the DevOps agent's review of a service.yaml change, either by changing the spec or by explaining with numbers why the code needs it. Use when the DevOps agent requests changes on a dev PR.
---

# Answer a DevOps review of service.yaml

Status: phase 1 outline. Written out and tested in phase 4.

Input: a PR in the current app repo with review comments from the DevOps agent.

1. Read each comment and the platform rule it cites (quota, policy, cost, missing health check).
2. For each one, decide whether to change the spec (and the code, if it has to change too) or
   keep it and explain why. An explanation gives numbers: measured memory, request rate, or the
   outside host the code has to reach and what for.
3. Reply on each comment thread with what you did. Leave the threads for the DevOps agent to
   resolve.
4. If the same request has come up before, say so in the PR's Lesson field: the contract or a
   skill may need to change so it stops recurring.

Done when: every review thread has a reply and the spec validates.
