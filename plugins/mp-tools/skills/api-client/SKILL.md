---
name: mp-api-client
description: This skill should be used when interacting with Mountain Project API endpoints, especially getPhotosTopos for areas and routes. Use for testing API responses, debugging topo data, fetching photo metadata, or exploring API behavior during development.
---

# Mountain Project API Client

Interact with Mountain Project API endpoints to test responses, debug topo overlays, fetch route/area data, and validate API integration during development.

## Purpose

This skill provides tools for making authenticated and unauthenticated calls to the Mountain Project API. It focuses on the `getPhotosTopos` endpoint (used for interactive topo features) but supports all major API endpoints including photos, ticks, packages, and route information.

## When to Use This Skill

Use this skill when:

- Testing the `getPhotosTopos` endpoint for areas or routes
- Debugging topo overlay data structure and rendering issues
- Fetching photo metadata for specific areas or routes
- Exploring API responses during feature development
- Validating API integration in the iOS app
- Investigating data sync issues
- Testing API behavior with different parameters
- Retrieving package information for offline data

## Available Endpoints

The skill supports these Mountain Project API endpoints:

- **getPhotosTopos** - Fetch topo overlays, relations, images, and users (primary endpoint)
- **getPhotos** - Get images without topo data
- **getTicks** - Get climbing logs for a route
- **getPackageList** - List available offline data packages
- **getPackageForArea** - Get package ID for an area
- **getPackageForRoute** - Get package ID for a route
- **getRouteInfo** - Get detailed route information

## Using the API Client Script

The skill includes a TypeScript script (`scripts/mp-api.ts`) for making API calls from the command line.

### Prerequisites

Ensure Node.js is installed and `tsx` is available for running TypeScript:

```bash
# Check if tsx is available
which tsx || npm install -g tsx
```

### Basic Usage Pattern

Execute the script with an action and required parameters:

```bash
cd ~/.claude/plugins/marketplaces/fx-cc/plugins/mp-tools/skills/api-client/scripts
npx tsx mp-api.ts <action> [options]
```

### Examples

#### Fetch Topos for an Area

```bash
npx tsx mp-api.ts getPhotosTopos --areaId 105717538
```

This returns:
- `users[]` - Array of user objects (id, firstName, lastName, avatar)
- `images[]` - Array of photo objects with sizes and metadata
- `topos[]` - Array of topo overlays with encoded topoData
- `topoRelations[]` - Array linking topos to routes with pitch info

#### Fetch Topos for a Route

```bash
npx tsx mp-api.ts getPhotosTopos --routeId 105717329
```

Returns the same structure as area query, but filtered to the specific route.

#### Fetch Photos Without Topos

```bash
npx tsx mp-api.ts getPhotos --areaId 105717538
npx tsx mp-api.ts getPhotos --routeId 105717329
```

#### Get Ticks for a Route

```bash
npx tsx mp-api.ts getTicks --routeId 105717329
```

#### List Available Packages

```bash
npx tsx mp-api.ts getPackageList
```

#### Get Package ID for Area or Route

```bash
npx tsx mp-api.ts getPackageForArea --areaId 105717538
npx tsx mp-api.ts getPackageForRoute --routeId 105717329
```

#### Get Route Information

```bash
npx tsx mp-api.ts getRouteInfo --routeIds 105717329,105748429
```

### Working with getPhotosTopos Response

The `getPhotosTopos` response includes topo overlay data in the `topoData` field of each topo object. This field is a JSON-encoded string that must be decoded separately.

#### TopoData Structure

Each topo's `topoData` contains an array of drawing items:

```json
{
  "items": [
    {
      "it": 0,
      "cp": [{"x": 100, "y": 200}, {"x": 150, "y": 300}],
      "ic": "#FF0000",
      "lw": 2,
      "ia": 1.0
    }
  ]
}
```

#### Item Types

- **0** (Line) - Route path with controlPoints array
- **1** (Bolt) - Protection marker at x,y
- **2** (Rappel) - Descent marker at x,y
- **3** (Belay) - Belay station at x,y
- **5** (Text) - Route label with text and alignment
- **6** (Piton) - Fixed gear marker at x,y

#### Extracting and Analyzing TopoData

To analyze topo overlay data:

```bash
# Fetch topos and save to file
npx tsx mp-api.ts getPhotosTopos --routeId 105717329 > response.json

# Extract topoData from a specific topo
cat response.json | jq '.topos[0].topoData | fromjson'
```

### Common Testing Patterns

#### Test Topo Rendering for a Specific Route

1. Fetch the topos:
   ```bash
   npx tsx mp-api.ts getPhotosTopos --routeId 105717329 > route-topos.json
   ```

2. Examine the structure:
   ```bash
   cat route-topos.json | jq '.topoRelations[] | .relation | {id, parentId, pitch, topoId, imageId}'
   ```

3. Decode topoData for analysis:
   ```bash
   cat route-topos.json | jq '.topos[0].topoData | fromjson | .items[] | select(.it == 0)'
   ```

#### Verify Image Metadata

```bash
npx tsx mp-api.ts getPhotosTopos --areaId 105717538 | jq '.images[] | {id, text, userId, sizes}'
```

#### Check Topo Relations for an Area

```bash
npx tsx mp-api.ts getPhotosTopos --areaId 105717538 | jq '.topoRelations[] | .relation | {parentId, pitch, type}'
```

## API Reference Documentation

The skill includes comprehensive API endpoint documentation in `references/api-endpoints.md`. Refer to this file for:

- Complete parameter lists for all endpoints
- Response structure details
- TopoData format specifications
- Item type definitions
- Coordinate space information
- Error handling patterns

Load the reference file when detailed API information is needed:

```bash
cat ~/.claude/plugins/marketplaces/fx-cc/plugins/mp-tools/skills/api-client/references/api-endpoints.md
```

## Authentication

The current implementation uses **anonymous/unauthenticated** API calls. Most read endpoints (getPhotosTopos, getPhotos, getPackageList) work without authentication.

For endpoints requiring authentication (sync endpoints, user-specific data), authentication headers would need to be added to the script.

## Workflow Integration

### During Feature Development

When implementing topo-related features:

1. Use this skill to fetch real API responses
2. Examine the actual data structure
3. Test edge cases (multiple pitches, missing data, etc.)
4. Validate iOS app parsing against API responses

### When Debugging

When investigating topo display issues:

1. Fetch topos for the problematic route/area
2. Compare API response with app's Realm database
3. Verify topoData decoding matches expectations
4. Check topo relations link correctly to routes

### During Testing

When validating API integration:

1. Test with known good area/route IDs
2. Verify response structure matches documentation
3. Check edge cases (no topos, many topos, etc.)
4. Validate data types and required fields

## Known Area and Route IDs for Testing

Refer to the iOS codebase for test IDs:

- Check `MountainProjectTests/Topo/DownloadToposOperationTests.swift` for test fixtures
- Check `Docs/GetPhotosTopos.md` for example IDs
- Use Mountain Project website URLs (e.g., `/route/105717329-...`) to extract IDs

## Error Handling

The script returns HTTP status codes and JSON error messages:

- **200** - Success
- **4xx** - Client error (invalid parameters, not found, etc.)
- **5xx** - Server error

Parse the output with `jq` or check exit codes in scripts:

```bash
if npx tsx mp-api.ts getPhotosTopos --routeId 105717329 > output.json; then
  echo "Success"
  cat output.json | jq .
else
  echo "Failed"
fi
```

## Extending the Script

To add support for additional endpoints:

1. Add a function to `scripts/mp-api.ts` following the existing pattern
2. Add a case to the CLI switch statement
3. Update the help text with the new action
4. Document the endpoint in `references/api-endpoints.md`

## Tips

- Use `jq` for JSON parsing and filtering in the terminal
- Save responses to files for comparison during debugging
- Pipe output to `jq '.topos'` to focus on specific sections
- Use `--areaId` for testing multi-route topos
- Use `--routeId` for testing single-route scenarios
- Compare API responses with iOS app's `RealmModelMapper.swift` logic
- Check coordinate scaling when debugging topo overlay rendering
