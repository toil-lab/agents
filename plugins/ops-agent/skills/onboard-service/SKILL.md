---
name: onboard-service
description: Turn a service's reviewed service.yaml into a deployment on the platform, with chart values, NetworkPolicy allows, secrets wiring, scaling, and an Argo CD application. Use after a new or changed service.yaml is approved.
---

# Onboard a service

Status: phase 1 outline. Written out and tested in phase 4.

Input: an app PR with an approved `service.yaml`, or a merged one.

1. Map each field to platform objects:
   - `kind` to a Deployment or CronJob
   - `resources` to requests
   - `scaling` to an HPA (cpu) or a KEDA ScaledObject (queue)
   - `exposes` to an Ingress
   - `depends_on` and `egress` to NetworkPolicy allows
   - `secrets` to Secret references
   - `backing` to the platform's Postgres or Redis definitions
2. Write the values and the Argo CD Application in the platform repo.
3. Render everything with `helm template` and run the platform-reviewer subagent on it.
4. State the RAM and CPU the service adds, then open the platform PR and link the app PR.

Done when: Argo CD shows the service synced and healthy in the team's dev namespace.
