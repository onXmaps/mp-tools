---
name: datapack-audit
description: This skill should be used when auditing mobile data packs in the adventure-project repo to find missing, failed, corrupt, or stale packs. Use when the user says "audit data packs", "check if packs failed", "find missing data packs", "which data packs failed to generate", or "validate mobile packages". Covers all project types (climb, hike, mtb, ski, trailrun).
---

# Data Pack Audit

Audit mobile data packs in the adventure-project repo to identify packs that failed to generate, are missing, corrupt, stale, or (for Climb) missing topo content.

## Purpose

Data packs are weekly-generated gzip files served to mobile apps for offline use. Generation failures result in missing or malformed files. This skill provides a workflow to detect failures across all project types and report actionable findings.

For full architecture details, record types, artisan commands, and failure modes, read the reference file:
`references/datapack-architecture.md` (in this skill's directory)

## Audit Workflow

### Step 1: Quick Filesystem Audit

Run the bundled script from the adventure-project repo root to scan all pack files on disk:

```bash
# All projects
bash <skill-dir>/scripts/audit-datapack-files.sh

# Single project
bash <skill-dir>/scripts/audit-datapack-files.sh climb
```

The script reports each pack's status:
- **OK** — file exists, size looks reasonable, not stale
- **FAIL** — file missing or suspiciously small (<1KB)
- **STALE** — file is older than 14 days (generation runs weekly; >14 days indicates a missed run)
- **WARN** — minor issue (e.g., missing `.txt` companion file)

The script exits non-zero if any FAILures are found.

### Step 2: Artisan Validation (optional, runs in Docker)

To run the server-side validation logic (which also checks pack format and ID correctness):

```bash
# Validate all areas for a project type
npm run php:artisan -- ap:validateMobilePackagesV2 {projectType}

# Validate a specific area
npm run php:artisan -- ap:validateMobilePackagesV2 {projectType} {areaId}
```

**WARNING:** This command automatically triggers regeneration for any pack it finds invalid. Run it only when repair is acceptable. Output lines containing `===== [ERROR]` indicate failures.

### Step 3: Climb Topo Verification (Climb only)

For Climb packs, the above checks do not validate topo content. Use the Python verifier:

```bash
python3 bin/verify_datapack.py \
  --url "https://local.mountainproject.com/api?action=getPackageData&id={areaId}&apiVersion=2" \
  --out-prefix /tmp/V2-{areaId}
```

A pack **FAILS** topo verification if:
- No TYPE=11 (TOPO) records are present, OR
- No areas or routes contain `topoRelations`

The script exits 0 on PASS, 1 on FAIL.

### Step 4: Report Findings

After running the above steps, report:
1. Which packs are missing (never generated or deleted)
2. Which packs are malformed (wrong ID, wrong format)
3. Which packs are stale (generation appears to have been skipped)
4. For Climb: which packs are missing topo content

Include area IDs and project types in the report so the user can target specific regeneration commands.

## Regeneration Commands

To regenerate a specific failing pack without triggering the full validation:

```bash
# AP projects (hike, mtb, ski, trailrun)
npm run php:artisan -- ap:createMobilePackagesV2 {projectType} {areaId}

# Climb
npm run php:artisan -- ap:createMobilePackagesMPV2 climb {areaId}

# Regenerate ALL packs for a project (long-running)
npm run php:artisan -- ap:createMobilePackagesV2 {projectType}
npm run php:artisan -- ap:createMobilePackagesMPV2 climb
```

## Key Paths

- Pack files: `site/public/assets/mobile/{projectType}/V2-{areaId}.txt.gz`
- Artisan commands: run via `npm run php:artisan --` (executes inside Docker `jobs` container)
- Python verifier: `bin/verify_datapack.py` (run directly on host, requires Python 3)
