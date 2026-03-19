---
name: mp-deployment-status
description: This skill should be used when checking whether an adventure-project PR, branch, or commit has been deployed to the Daily or Production environments. Use when the user asks "is this PR on prod?", "has this been deployed?", "is X on daily?", "when did this get released?", or similar deployment status questions.
---

# Adventure Project Deployment Status

Check whether a given PR, branch, or commit from `adventure-project` has been deployed to Daily or Production.

## Purpose

Deployments to Daily and Production are tracked via `container_tag` values in the atlantis-adventure-project Terraform repo. Each `container_tag` is a short git SHA from the `adventure-project` repo. To determine if a commit is deployed, compare the `container_tag` in each environment's tfvars file against the commit in question using `git merge-base --is-ancestor`.

## Repo Locations

| Repo | Path |
|------|------|
| Application code | `~/Code/onX/adventure-project` |
| Terraform / deployments | `~/Code/onX/atlantis-adventure-project` |

## Environment tfvars Files

| Environment | File |
|-------------|------|
| Daily | `~/Code/onX/atlantis-adventure-project/onx-daily.tfvars` |
| Production | `~/Code/onX/atlantis-adventure-project/onx-production.tfvars` |

The `container_tag` inside `project_deployments` in each tfvars file is the deployed git SHA (short form).

## Workflow

### Step 1 — Resolve the commit SHA

Determine the full commit SHA for the thing being checked:

**If given a PR number:**
```bash
gh pr view <NUMBER> --repo onXmaps/adventure-project --json mergedAt,mergeCommit,state
```
Use `mergeCommit.oid` as the commit. If `state` is not `MERGED`, warn the user — unmerged PRs cannot be deployed.

**If given a branch name:**
```bash
cd ~/Code/onX/adventure-project && git rev-parse origin/<branch>
# or: git ls-remote origin <branch>
```

**If given a commit SHA already:** use it directly.

### Step 2 — Read the deployed container tags

```bash
grep 'container_tag' ~/Code/onX/atlantis-adventure-project/onx-daily.tfvars | head -1
grep 'container_tag' ~/Code/onX/atlantis-adventure-project/onx-production.tfvars | head -1
```

Extract the short SHA value (e.g., `3851dac`) from each file. The relevant line is the one inside the `project_deployments` block (the first `container_tag` in the file).

### Step 3 — Compare commits

In the `adventure-project` repo, check whether the target commit is an ancestor of (i.e., included in) each deployed tag:

```bash
cd ~/Code/onX/adventure-project

# Returns exit code 0 if TARGET is an ancestor of DEPLOYED (i.e., deployed)
git merge-base --is-ancestor <TARGET_SHA> <DEPLOYED_TAG> && echo "YES" || echo "NO"
```

Run this for both Daily and Production tags.

If the local repo is stale, fetch first:
```bash
git fetch origin
```

### Step 4 — Report results

Return a clear summary:

```
PR #823 — Add elevation profile endpoint

Daily:      ✅ Deployed  (daily tag: 3851dac, merged 2026-03-12)
Production: ❌ Not yet   (prod tag:  a4a6c19, which predates this PR)
```

If both environments are behind, note which PRs/commits are queued between the deployed tag and the target. Use `git log <deployed_tag>..<target_sha> --oneline` to show what's pending.

## Notes

- The `container_tag` inside `standalone_deployments` blocks (e.g., `mtn-project-admin`, `backend-subgraph`) are for separate services — ignore those when checking adventure-project deployments.
- If the atlantis repo is out of date, pull it: `cd ~/Code/onX/atlantis-adventure-project && git pull`.
- Production deploys lag behind Daily — a PR must be on Daily before it can reach Production.
- Deployment to Production requires someone to update `container_tag` in `onx-production.tfvars` and apply via Atlantis. If a PR is on Daily but not Production, it's awaiting a prod deploy.
