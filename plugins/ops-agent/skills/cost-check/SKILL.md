---
name: cost-check
description: Estimate the cloud cost of a change before anything is applied, and say whether it stays inside the free tier. Use before any terraform apply, gcloud change, or GKE action.
---

# Check the cost of a change

Status: phase 1 outline. Written out and tested in phase 5.

1. List every resource the change creates or modifies, from `terraform plan` or the gcloud
   command.
2. For each one, find the price and whether a free-tier limit covers it. Use the provider's
   current pricing page, and say which page you read and when.
3. Give the expected monthly cost, and the cost if usage doubles.
4. Post the result on the PR or issue before asking for approval. The GCP spend guard stops the
   command for the approver either way.

Done when: the PR or issue shows the cost estimate and its sources.
