# Testing the Mountain Project API Client Skill

This document provides test results and usage examples for the mp-api-client skill.

## Test Results

### ✅ getPackageList

Successfully retrieves the list of available offline data packages:

```bash
cd ~/.claude/plugins/marketplaces/fx-cc/plugins/mp-tools/skills/api-client/scripts
npx tsx mp-api.ts getPackageList
```

Returns packages for all US states and international areas with metadata (id, title, size, coordinates, route count).

### ✅ getPhotosTopos (Route)

Successfully retrieves photos and topo data for routes:

```bash
npx tsx mp-api.ts getPhotosTopos --routeId 105748577
```

Returns:
- `users[]` - Array of users who contributed photos/topos
- `images[]` - Photo metadata with multiple sizes
- `topoRelations[]` - Relationships between topos and routes (may be empty)
- `topos[]` - Interactive topo overlay data (may be empty)

### ✅ getPhotosTopos (Area)

Successfully makes API call for areas:

```bash
npx tsx mp-api.ts getPhotosTopos --areaId 105717538
```

Note: Some areas may return empty arrays if they don't have topo overlays configured.

## Configuration

The script uses these default values:

- **Base URL:** `https://www.mountainproject.com/api`
- **API Version:** 2
- **OS:** iOS 18.0
- **App Version:** 4.5.0
- **Device ID:** `00000000-0000-0000-0000-000000000000` (can be overridden via `MP_DEVICE_ID` env var)

## Customization

Set a custom device ID:

```bash
export MP_DEVICE_ID="your-device-id"
npx tsx mp-api.ts getPackageList
```

## Known Limitations

1. **Anonymous Access** - Some endpoints may require authentication (user ID + security hash)
2. **Empty Topo Data** - Not all routes/areas have interactive topos configured
3. **Rate Limiting** - No official limits documented, but use reasonable request intervals

## Finding Test IDs

To find valid route/area IDs for testing:

1. Browse [MountainProject.com](https://www.mountainproject.com)
2. Copy the ID from URLs like: `/route/105748577-...` or `/area/105717538-...`
3. Use popular areas like:
   - **Eldorado Canyon** (Colorado package: 105708956)
   - **Red Rocks** (Nevada)
   - **Yosemite** (California package: 105708959)

## Integration with iOS App

The API responses match the structure expected by:

- `CoreMp/MpApi.swift` - iOS API client
- `CoreMp/RealmModelMapper.swift` - Response parsing
- `CoreMp/DownloadAllPhotosOperation.swift` - Data sync operations

## Next Steps

To extend the skill:

1. Add authentication support (user ID + security hash)
2. Implement sync endpoints (ticks, todos, ratings)
3. Add caching to reduce API calls during development
4. Create test fixtures based on real API responses
