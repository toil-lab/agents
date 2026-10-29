---
name: build-feature
description: Turn a GitHub feature issue in an app repo into code, tests, Dockerfile and service.yaml changes, and a pull request. Use when the developer agent picks up a feature issue.
---

# Build a feature from an issue

Status: phase 1 outline. Written out and tested in phase 4.

Input: a feature issue number in the current app repo.

1. Read the issue and its links. If the acceptance criteria are unclear, ask on the issue
   before writing code.
2. Create the branch `<issue-number>-<short-name>`.
3. Write the code and its tests. Run the unit tests.
4. Compare what the code now needs with `service.yaml`: environment variables, port, health
   paths, dependencies, outside hosts, CPU and memory. Update the spec and validate it with
   `contract/validate.py`.
5. Run the code-reviewer subagent on the diff and fix its findings.
6. Commit with the trailer `Agent: dev`, push, and open the PR with the template filled in.
   Say in the description whether `service.yaml` changed, so the DevOps agent knows a review
   is coming.

Done when: the PR is open, CI is green, and the issue is linked.
