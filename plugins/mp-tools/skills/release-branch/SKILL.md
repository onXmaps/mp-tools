---
name: mp-release-branch
description: This skill should be used when cutting a CoreAP release branch. It reads the current version from Base.xcconfig, proposes the rc-v<VERSION> branch name, updates CHANGELOG.md with changes since the last release, generates a QA test plan in Docs/, commits both, pushes the branch, and opens a PR targeting intere/latest.
---

# CoreAP Release Branch

Cut a release branch for the CoreAP iOS monorepo, update the changelog, and open a PR.

## Purpose

Automate the CoreAP release branch workflow: read the current marketing version, propose the release branch name, update CHANGELOG.md with changes since the last release, generate a QA test plan, push the branch, and create a PR targeting `intere/latest`.

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

### Step 6 — Generate the QA test plan

**Scope:** The test plan covers only what is **new since the previous release**. Read the two most recent entries in `CHANGELOG.md` to establish the diff:

- **Current version** (`<VERSION>`) — the entry you just wrote/updated in Step 4.
- **Previous version** (`<PREV_VERSION>`) — the entry immediately below it in the file.

Any item that appears in **both** entries (i.e., was already shipped in `<PREV_VERSION>`) must be **excluded** from the test plan. Only items present in `<VERSION>` but absent from `<PREV_VERSION>` belong in the plan.

Create `Docs/TestPlan-<VERSION>.md` using this structure:

```markdown
# QA Test Plan — <VERSION>

**Release branch:** `rc-v<VERSION>`
**Date:** <TODAY>
**Scope:** Changes since <PREV_VERSION>
**Apps in scope:** <list primary apps affected by this release>

---

## <Feature or area name> (<ticket>, <PR>)

### <Sub-scenario>
- [ ] <Step-by-step test case with clear pass/fail criteria>
- [ ] <Edge case or offline scenario>
...

---

## Crash regression

New crash fixes since <PREV_VERSION> (omit any fixed in <PREV_VERSION> or earlier):

| Crash | Steps to reproduce |
|---|---|
| <description> | <minimal repro steps> |

---

## Smoke test

Quick pass to confirm nothing regressed.

- [ ] Search for a route by name. Navigate to the route detail screen.
- [ ] Open an area. Browse sub-areas and routes.
- [ ] Download a single data pack. Verify it installs and offline data is accessible.
- [ ] Log out and log back in.

---

## Devices / OS

Run critical paths on at minimum:

| Device | OS |
|---|---|
| iPhone 16 Pro | iOS 18.x |
| iPhone SE (3rd gen) | iOS 17.x |
| iPad (any) | iOS 17.x |

---

## Notes

<Any prerequisite state, test accounts, feature flags, or backend dependencies.>
```

**Rules for populating test cases:**
- **Only include items new since `<PREV_VERSION>`.** If a feature or fix appears in `<PREV_VERSION>`'s CHANGELOG entry, omit it entirely — it was already QA'd.
- Write one section per feature or significant bug fix that is new in this release.
- Each section must include a happy-path case, at least one edge case, and (where applicable) an offline/network-interrupted case.
- Crash fixes get a row in the **Crash regression** table, not a full section. Only include crashes first fixed in `<VERSION>`.
- Reference the CHANGELOG ticket/PR numbers in each section header.
- Keep steps imperative and unambiguous — a QA engineer with no implementation knowledge should be able to follow them.
- Note any backend or feature-flag prerequisites in the Notes section (e.g., a server-side PR that must be deployed before testing).

### Step 7 — Commit changelog and test plan

Stage and commit both files together:

```bash
git add CHANGELOG.md Docs/TestPlan-<VERSION>.md
git commit -m "📝 Update CHANGELOG and add QA test plan for rc-v<VERSION>"
```

### Step 8 — Push the branch

```bash
git push -u origin rc-v<VERSION>
```

### Step 9 — Create the PR

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
- [ ] QA test plan reviewed (`Docs/TestPlan-<VERSION>.md`)
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
| `Docs/TestPlan-<VERSION>.md` | QA test plan — generated from CHANGELOG, committed with the branch |

## Conventions

- Branch format: `rc-v<MAJOR>.<MINOR>.<PATCH>` (e.g., `rc-v4.6.14`)
- Commit message format: `📝 Update CHANGELOG for rc-v<VERSION>` (gitmoji style, no trailing period)
- CHANGELOG date format: `YYYY-MM-DD`
- PR base branch: always `intere/latest`
- Always add `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` to the commit
