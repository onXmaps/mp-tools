# Data Pack Architecture Reference

## Overview

Data packs are gzip-compressed offline content packages served to mobile apps. Each pack covers one top-level geographic area.

## Project Types

| projectType | Platform |
|-------------|----------|
| `climb`     | Mountain Project |
| `hike`      | Hiking Project |
| `mtb`       | MTB Project |
| `ski`       | Powder Project |
| `trailrun`  | Trail Run Project |

## Storage Paths

**Public filesystem path:**
```
site/public/assets/mobile/{projectType}/V2-{areaId}.txt.gz   ← distributed
site/public/assets/mobile/{projectType}/V2-{areaId}.txt      ← uncompressed (rarely used)
```

**Special case (hike):**
```
site/public/assets/mobile/hike/V2-NP.txt.gz   ← national parks bundle
```

## Artisan Commands

```bash
# Validate (read-only audit → triggers regen on failure)
npm run php:artisan -- ap:validateMobilePackagesV2 {projectType}
npm run php:artisan -- ap:validateMobilePackagesV2 {projectType} {areaId}

# Generate
npm run php:artisan -- ap:createMobilePackagesV2 {projectType}
npm run php:artisan -- ap:createMobilePackagesV2 {projectType} {areaId}

# Climb-specific generate
npm run php:artisan -- ap:createMobilePackagesMPV2 climb
npm run php:artisan -- ap:createMobilePackagesMPV2 climb {areaId}
```

**IMPORTANT:** `validateMobilePackagesV2` automatically calls `createMobilePackages*V2` when it detects a missing or malformed pack. Running it is both an audit and a repair operation.

## Failure Detection (ValidateMobilePackagesV2)

The validate command checks each area's pack for:
1. Both `.txt` and `.txt.gz` files exist
2. AP projects (non-climb): First line matches `Package_{id}_{timestamp}_{json}` format
3. AP projects: ID in filename matches area ID
4. AP projects: Timestamp > 166883200 (ensures it's a real date)

Log output prefixes:
- `===== [ERROR]` — pack missing, wrong format, wrong ID, or outdated → triggers regen
- No error line → pack is healthy

## Climb-Specific Validation (bin/verify_datapack.py)

For Climb packs, the standard validate command does NOT check topo content. Use the Python verifier:

```bash
# Against a local pack file (skip fetch step with --url pointing to local server)
python3 bin/verify_datapack.py \
  --url "https://local.mountainproject.com/api?action=getPackageData&id={areaId}&apiVersion=2" \
  --out-prefix /tmp/V2-{areaId}

# The script exits 0 = PASS, 1 = FAIL
```

**Pass criteria for Climb packs:**
- At least 1 TYPE=11 (TOPO) record present
- At least 1 area OR route with `topoRelations` present

## Record Types (Climb packs, binary framed format)

```
Frame structure: [8 bytes length LE][8 bytes type LE][N bytes UTF-8 JSON]
```

| Type | Content |
|------|---------|
| 1  | PACKAGE (metadata header) |
| 2  | AREA |
| 3  | ROUTE |
| 4  | IMAGES |
| 5  | COMMENTS |
| 6  | TICKS |
| 7  | ACCESS_NOTE |
| 8  | TEXT_SECTIONS |
| 9  | USER |
| 10 | TRAIL |
| 11 | TOPO |

## Common Failure Modes

1. **File missing** — generation job never ran or crashed
2. **Zero or tiny file** — generation started but aborted (DB timeout, OOM, etc.)
3. **Wrong format/ID** — corrupted write or filesystem issue
4. **Outdated** — timestamp too old (pre-1975 epoch)
5. **Climb: no topos** — topo data missing from pack despite file existing (checked by verify_datapack.py)
6. **Stale** — file exists and passes format checks but is older than expected (generation runs weekly on Saturdays at 20:00 UTC)

## Serving

- **AP projects:** `GET /api?action=getPackageData&id={areaId}&apiVersion=2` → redirects to CDN
- **All projects:** `GET /api?action=getPackageList&apiVersion=2` → cached list of available packs

## Source Files

| Purpose | Path |
|---------|------|
| AP generation | `site/app/Console/Commands/DataPacks/CreateMobilePackagesV2.php` |
| Climb generation | `site/app/Console/Commands/Climb/CreateMobilePackagesMPV2.php` |
| Validation | `site/app/Console/Commands/DataPacks/ValidateMobilePackagesV2.php` |
| Topo verifier | `bin/verify_datapack.py` |
| AP pack list API | `site/app/Http/Controllers/Api/Mobile/GetPackageList.php` |
| Climb pack list API | `packages/projects/climb/app/Http/Controllers/Api/Mobile/Climb/GetPackageList.php` |
| Scheduling | `site/app/Console/Kernel.php` (lines ~134-135, Saturdays 20:00 UTC) |
