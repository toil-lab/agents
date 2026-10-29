---
name: onboard-team
description: Give a new team its namespaces, quotas, NetworkPolicies, Argo CD project, kubeconfig contexts, and GitHub team and CODEOWNERS entries on the platform. Use when an onboard-team issue opens in the platform repo.
---

# Onboard a team

Status: phase 1 outline. Written out and tested in phase 3.

Input: an onboard-team issue naming the team, its app repo, and its members.

1. Create `<team>-dev` and `<team>-staging` namespaces with a ResourceQuota and LimitRange
   sized to the host budget.
2. Add default-deny ingress and egress NetworkPolicies, plus an egress allow for DNS.
3. Create the Argo CD AppProject. Its source is the team's repo and its destinations are the
   team's namespaces only.
4. Create the ServiceAccounts and RoleBindings behind `claude-<team>-dev` (edit in dev) and
   `claude-<team>-logs` (read pods, logs, and events in dev). Write their kubeconfig entries
   with the platform's credential script, never into the repo.
5. Add the GitHub team, its CODEOWNERS entries, and its Projects board view through the
   workspace Terraform.
6. State the RAM the quotas reserve, then open the PR.

Done when: the team can deploy to its namespaces and is refused in every other team's.
