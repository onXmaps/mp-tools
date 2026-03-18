---
name: mp-release-branch
description: This skill should be used when cutting a CoreAP release branch. It reads the current version from Base.xcconfig, proposes the rc-v<VERSION> branch name, updates CHANGELOG.md with changes since the last release, commits, pushes the branch, and opens a PR targeting intere/latest.
---

# CoreAP Release Branch

Cut a release branch for the CoreAP iOS monorepo, update the changelog, and open a PR.

## Purpose

Automate the CoreAP release branch workflow: read the current marketing version, propose the release branch name, update CHANGELOG.md with changes since the last release, push the branch, and create a PR targeting `intere/latest`.

## Workflow

### Step 1 — Read the current version

Read `Base.xcconfig` in the repo root and extract `MARKETING_VERSION`:

```bash
grep MARKETING_VERSION Base.xcconfig
# Example output: MARKETING_VERSION = 4.6.14
```

Propose the release branch name: `rc-v<MARKETING_VERSION>` (e.g., `rc-v4.6.14`).

Confirm with the user before proceeding. If they want a different version, use their value.

### Step 2 — Verify git state

```bash
git status
git branch --show-current
```

Warn the user if there are uncommitted changes. The skill may still proceed if the user confirms, but note that uncommitted changes will NOT be included in the release branch.

### Step 3 — Identify changes since last release

Find the previous release tag or branch point to scope the git log:

```bash
# Find the most recent rc-v* tag or the latest release in CHANGELOG.md
git tag --sort=-creatordate | grep '^rc-v\|^v' | head -5

# Get commits since last release tag (adjust tag name as needed)
git log <last-tag>..HEAD --oneline --no-merges
```

If no tag is found, fall back to comparing against the `develop` branch's divergence point or the previous version listed in CHANGELOG.md.

### Step 4 — Update CHANGELOG.md

Open `CHANGELOG.md` and inspect the top entry:

**Case A — Top entry is `[VERSION] — Unreleased (RC)` and VERSION matches current:**
- Replace `Unreleased (RC)` with today's date in `YYYY-MM-DD` format.
- Review the existing bullet points against the git log from Step 3. Add any significant missing changes.

**Case B — Top entry is for a different version (no entry yet for current):**
- Insert a new section above the existing top entry using this template:
  ```markdown
  ## [<VERSION>] — <TODAY>

  ### Features
  - <items from git log>

  ### Bug Fixes
  - <items from git log>

  ---
  ```
- Populate bullet points from the git log. Group into Features and Bug Fixes based on commit messages (✨/feat → Features; 🐛/fix → Bug Fixes). Use the gitmoji and PR/ticket references from commit messages. Skip merge commits and version-bump commits.

Keep entries concise — one line per meaningful change, referencing the PR number or Jira ticket where visible in the commit message.

### Step 5 — Cut the release branch

```bash
git checkout -b rc-v<VERSION>
```

### Step 6 — Commit the changelog update

Stage and commit only the CHANGELOG.md change:

```bash
git add CHANGELOG.md
git commit -m "📝 Update CHANGELOG for rc-v<VERSION>"
```

### Step 7 — Push the branch

```bash
git push -u origin rc-v<VERSION>
```

### Step 8 — Create the PR

Use the `gh` CLI to create a PR targeting `intere/latest`:

```bash
gh pr create \
  --base intere/latest \
  --title "rc-v<VERSION>" \
  --body "$(cat <<'EOF'
## Release rc-v<VERSION>

<paste the relevant CHANGELOG section here>

## Checklist
- [ ] CHANGELOG reviewed
- [ ] Version confirmed in Base.xcconfig
- [ ] CI passes
EOF
)"
```

Populate the PR body with the CHANGELOG section for this version. Return the PR URL to the user when done.

## Key Files

| File | Purpose |
|------|---------|
| `Base.xcconfig` | Version source — `MARKETING_VERSION` |
| `CHANGELOG.md` | Release notes — update before committing |

## Conventions

- Branch format: `rc-v<MAJOR>.<MINOR>.<PATCH>` (e.g., `rc-v4.6.14`)
- Commit message format: `📝 Update CHANGELOG for rc-v<VERSION>` (gitmoji style, no trailing period)
- CHANGELOG date format: `YYYY-MM-DD`
- PR base branch: always `intere/latest`
- Always add `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` to the commit
