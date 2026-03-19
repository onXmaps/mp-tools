# Mountain Project Tools (mp-tools)

A standalone Claude Code plugin for Mountain Project / onX Adventure development. Provides skills for API testing, debugging topo overlays, auditing data packs, managing release branches, and checking deployment status.

## Installation

Install as a local Claude Code plugin:

```bash
claude plugin add /path/to/mp-tools
```

Or install directly from GitHub:

```bash
claude plugin add github:onXmaps/mp-tools
```

## Skills

### api-client

Interact with Mountain Project API endpoints to fetch topos, photos, routes, and packages.

**Use this skill when:**
- Testing the `getPhotosTopos` endpoint for areas or routes
- Debugging topo overlay data structure
- Fetching photo metadata
- Exploring API responses during development
- Validating API integration
- Investigating data sync issues

**Key features:**
- Command-line API client script (TypeScript)
- Support for all major Mountain Project endpoints
- Anonymous/unauthenticated access
- JSON output for easy parsing
- Comprehensive API reference documentation

**Example usage:**
```bash
# Fetch topos for an area
npx tsx mp-api.ts getPhotosTopos --areaId 105717538

# Fetch topos for a route
npx tsx mp-api.ts getPhotosTopos --routeId 105717329

# Get photos without topo data
npx tsx mp-api.ts getPhotos --areaId 105717538

# List available packages
npx tsx mp-api.ts getPackageList
```

See `skills/api-client/SKILL.md` for complete documentation.

### datapack-audit

Audit mobile data packs to find missing, failed, corrupt, or stale packs across all project types (climb, hike, mtb, ski, trailrun).

**Use this skill when:**
- Checking if data packs failed to generate
- Finding missing or malformed packs
- Verifying Climb packs contain topo content
- Investigating why offline data is missing or outdated

**Key features:**
- Filesystem audit script covering all project types
- Artisan validation workflow (with Docker)
- Climb topo verification via `bin/verify_datapack.py`
- Regeneration command reference

See `skills/datapack-audit/SKILL.md` for complete documentation.

### release-branch

Guidance for creating and managing Mountain Project release branches.

See `skills/release-branch/SKILL.md` for complete documentation.

### deployment-status

Check whether an `adventure-project` PR, branch, or commit has been deployed to the Daily or Production environments.

**Use this skill when:**
- Verifying if a merged PR has reached Production or Daily
- Answering questions like "is this on prod yet?" or "has X been deployed?"
- Checking which commits are queued between the current deployed tag and a target commit

**How it works:**
- Reads `container_tag` from `onx-daily.tfvars` and `onx-production.tfvars` in the `atlantis-adventure-project` repo
- Uses `git merge-base --is-ancestor` to determine if the target commit is included in each deployed tag
- Reports a clear ✅/❌ summary per environment

See `skills/deployment-status/SKILL.md` for complete documentation.

## Requirements

- Node.js (for running TypeScript scripts)
- `tsx` for executing TypeScript: `npm install -g tsx`
- `jq` (optional, for JSON parsing in terminal)

## Related Documentation

For Mountain Project / onX Adventure development, see:
- `CoreAP/Docs/GetPhotosTopos.md` — getPhotosTopos API documentation
- `CoreAP/Docs/Sync.md` — Sync endpoint documentation
- `CoreAP/CoreMp/MpApi.swift` — iOS API client implementation
- `CoreAP/CLAUDE.md` — Project overview and conventions

## Contributing

To add new skills or improve existing ones:

1. Create a new skill directory: `skills/<skill-name>/`
2. Add `SKILL.md` with proper frontmatter (`name` and `description` fields required)
3. Add `scripts/`, `references/`, or `assets/` as needed
4. Update this README
5. Test with Claude Code

## Version History

- **1.2.0** — Add `deployment-status` skill for checking Daily/Production deploy status
- **1.1.0** — Add `datapack-audit` skill for mobile data pack failure detection
- **1.0.0** — Initial release with `api-client` and `release-branch` skills
