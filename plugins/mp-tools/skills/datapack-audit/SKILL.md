---
name: datapack-audit
description: This skill should be used when auditing mobile data packs in the adventure-project to find missing, failed, corrupt, or stale packs in production. Use when the user says "audit data packs", "check if packs failed", "find missing data packs", "which data packs failed to generate", or "validate mobile packages". Covers all project types (climb, hike, mtb, ski, trailrun).
---

# Data Pack Audit

Audit production mobile data packs to identify packs that failed to generate, are suspiciously small, or are stale. Works against live production APIs — no local server or Docker required.

For full architecture details, record types, artisan commands, and failure modes, read:
`references/datapack-architecture.md` (in this skill's directory)

## Audit Workflow

### Step 1: Run the Production Audit Script

Run the bundled Python script from anywhere (no repo context needed):

```bash
# Audit all project types against production
python3 <skill-dir>/scripts/audit-production.py

# Audit a single project
python3 <skill-dir>/scripts/audit-production.py --project climb
python3 <skill-dir>/scripts/audit-production.py --project hike
```

The script:
1. Calls `getPackageList` on each project's production API to enumerate existing packs
2. **Climb**: checks the `size` field returned per-pack, checks `lastBuild` staleness
3. **AP projects** (hike/mtb/ski/trailrun): HEADs each CDN URL to get file size, checks `buildDate` per-pack

Each pack is reported as:
- **OK** — exists, size looks reasonable
- **FAIL** — zero size, too small (<50 KB), or CDN unreachable
- **STALE** — pack exists and passes size check but is older than 14 days

Exits non-zero if any FAILures are found.

**Important:** Packs that failed to generate entirely will NOT appear in `getPackageList` at all — the API silently omits areas with no file. A pack that is truly missing shows up as absent from the list, not as a FAIL row. To detect truly missing packs, compare the count against the expected number of top-level areas (see Step 2).

### Step 2: Interpret the Results

**Pack count sanity check** — compare the number reported against known baselines:

| Project | Expected packs (approx) |
|---------|------------------------|
| climb   | ~70–80 areas           |
| hike    | ~50–60 areas           |
| mtb     | ~40–50 areas           |
| ski     | ~20–30 areas           |
| trailrun| ~20–30 areas           |

If the count is significantly lower than expected, packs are missing from the list entirely (generation failure — file was never written).

**Climb `lastBuild`** — this is the most recent build time across ALL Climb packs. If it is >14 days old, the weekly generation job likely missed a run.

### Step 3: Verify Climb Topo Content (Climb only, as needed)

Standard size checks do not verify topo content. If Climb packs look structurally OK but topos are suspected missing:

```bash
# Download and analyze a specific Climb pack for topo records
python3 bin/verify_datapack.py \
  --url "https://www.mountainproject.com/api?action=getPackageData&id={areaId}&apiVersion=2&os=iOS&osVersion=18.0&v=4.6.0&deviceId=00000000-0000-0000-0000-000000000000" \
  --out-prefix /tmp/V2-{areaId}
```

A pack **FAILS** topo verification if:
- No TYPE=11 (TOPO) records are present, OR
- No areas or routes contain `topoRelations`

Run from the adventure-project repo root. Exits 0 on PASS, 1 on FAIL.

### Step 4: Trigger Regeneration (requires Docker / adventure-project repo)

To regenerate specific failing packs, run from the adventure-project repo root:

```bash
# AP projects (hike, mtb, ski, trailrun) — specific area
npm run php:artisan -- ap:createMobilePackagesV2 {projectType} {areaId}

# AP projects — all areas (long-running)
npm run php:artisan -- ap:createMobilePackagesV2 {projectType}

# Climb — specific area
npm run php:artisan -- ap:createMobilePackagesMPV2 climb {areaId}

# Climb — all areas (long-running)
npm run php:artisan -- ap:createMobilePackagesMPV2 climb

# Validate + auto-repair (runs regen for any missing/malformed pack)
npm run php:artisan -- ap:validateMobilePackagesV2 {projectType}
```

## Key Facts

- **CDN URL pattern**: `https://cdn2.apstatic.com/mobile/{projectType}/V2-{areaId}.txt.gz`
- **getPackageList**: public endpoint, no auth required
- **Climb response**: `{ packages: [{id, title, size, ...}], lastBuild }` — size is bytes per pack
- **AP response**: `[{id, title, buildDate, ...}]` — NO size field; must HEAD CDN for size
- **Generation schedule**: weekly, Saturdays 20:00 UTC
