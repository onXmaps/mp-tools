# Mountain Project API Endpoints Reference

This document provides comprehensive information about Mountain Project API endpoints, with special focus on the `getPhotosTopos` endpoint used for interactive topo features.

## Base Configuration

- **Base URL:** `https://www.mountainproject.com/api`
- **API Version:** 2
- **Method:** GET (unless specified otherwise)

### Standard Parameters

All API calls automatically include these parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `action` | The API action to perform | `getPhotosTopos` |
| `apiVersion` | API version number | `2` |
| `os` | Operating system | `iOS` |
| `osVersion` | OS version | `18.0` |
| `v` | Cache buster timestamp | `1708889234567` |

## getPhotosTopos

Fetches topo overlays, topo relations, images, and users for a given area or route. This is the primary endpoint for the interactive topo feature.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `areaId` | Int | One required | The area ID to fetch topos for |
| `routeId` | Int | One required | The route ID to fetch topos for |

**Note:** Provide either `areaId` OR `routeId`, not both.

### Response Structure

```json
{
    "users": [
        {
            "id": 200078886,
            "firstName": "John",
            "lastName": "Doe",
            "avatar": "https://example.com/avatar.jpg"
        }
    ],
    "images": [
        {
            "id": 113744585,
            "text": "Photo caption",
            "sizes": {
                "thumb": {
                    "url": "https://cdn-files.apstatic.com/climb/113744585_small_1508792027.jpg",
                    "w": 150,
                    "h": 200
                },
                "medium": {
                    "url": "https://cdn-files.apstatic.com/climb/113744585_medium_1508792027.jpg",
                    "w": 450,
                    "h": 600
                }
            },
            "scoreCount": 2,
            "scoreAvg": 5.0,
            "userId": 200078886
        }
    ],
    "topos": [
        {
            "id": "topo-uuid-string",
            "imageId": 113744585,
            "topoData": "{\"items\":[...]}"
        }
    ],
    "topoRelations": [
        {
            "relation": {
                "id": "relation-uuid-string",
                "parentId": 105717538,
                "topoId": "topo-uuid-string",
                "imageId": 113744585,
                "pitch": "1",
                "type": "route",
                "annotationIds": "ann-1,ann-2",
                "createdByMethod": "web",
                "createdByUserId": 200078886,
                "createDate": 1507128662
            }
        }
    ]
}
```

### Important Notes

- **`topoRelations`** can be either a dictionary (keyed by index) or an array
- **`topoData`** is a JSON-encoded string containing overlay items (lines, bolts, belays, etc.)
- **`images`** do NOT embed user objects directly; use `userId` to look up from `users` array
- When querying by `areaId`, `parentId` in each relation is a **route ID**, not the area ID
- When querying by `routeId`, filter to only relations where `parentId` matches the queried route

### TopoData Format

The `topoData` field is a JSON string that decodes to an array of `TopoItem` objects:

```json
{
    "items": [
        {
            "it": 0,
            "cp": [{"x": 100, "y": 200}, {"x": 150, "y": 300}],
            "ic": "#FF0000",
            "lw": 2,
            "ia": 1.0
        },
        {
            "it": 1,
            "x": 120,
            "y": 250,
            "ic": "#FF0000"
        },
        {
            "it": 5,
            "x": 100,
            "y": 180,
            "t": "Gripper 5.10a",
            "ic": "#FF0000",
            "ta": "c"
        }
    ]
}
```

#### Item Types (`it` field)

| Value | Type | Description | Uses |
|-------|------|-------------|------|
| 0 | Line | Route path line | `cp` (controlPoints array) |
| 1 | Bolt | Protection point marker | `x`, `y` |
| 2 | Rappel | Rappel/descent marker | `x`, `y` |
| 3 | Belay | Belay station marker | `x`, `y` |
| 5 | Text | Route label | `x`, `y`, `t` (text), `ta` (textAlign) |
| 6 | Piton | Piton/fixed-gear marker | `x`, `y` |

#### TopoItem Fields

| Field | Key | Type | Description |
|-------|-----|------|-------------|
| itemType | `it` | Int | Type of item (see table above) |
| controlPoints | `cp` | [{x, y}] | Array of coordinates for line items |
| x | `x` | Int | X coordinate (for point items) |
| y | `y` | Int | Y coordinate (for point items) |
| color | `ic` | String | Hex color (e.g., `"#FF0000"`) |
| text | `t` | String | Label text (for text items) |
| lineWidth | `lw` | Int | Line width (for line items) |
| alpha | `ia` | Float | Opacity (0.0 - 1.0) |
| textAlign | `ta` | String | Text alignment: `"l"`, `"c"`, `"r"` |
| width | `w` | Int | Width |
| height | `h` | Int | Height |

**Coordinate Space:** Coordinates are in original image pixel space and must be scaled to match displayed image dimensions.

## getPhotos

Get list of images for an area or route (without topo data).

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `areaId` | Int | One required | The area ID |
| `routeId` | Int | One required | The route ID |

### Response Structure

Array of image objects with embedded user information.

## getTicks

Get ticks (climbing logs) for a route.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `routeId` | Int | Yes | The route ID |

### Response Structure

Array of tick objects with route ID, date, style, notes, etc.

## getPackageList

Get list of available offline data packages.

### Request Parameters

None (uses standard parameters only).

### Response Structure

```json
{
    "lastBuild": 1708889234,
    "packages": [
        {
            "id": 105717538,
            "name": "Eldorado Canyon SP",
            "lat": 39.9311,
            "lon": -105.2856
        }
    ]
}
```

## getPackageForArea

Get the package ID for a given area.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | Int | Yes | The area ID |

### Response Structure

```json
{
    "id": 105717538
}
```

## getPackageForRoute

Get the package ID for a given route.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | Int | Yes | The route ID |

### Response Structure

```json
{
    "id": 105717538
}
```

## getRouteInfo

Get detailed information for one or more routes.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `routeIds` | String | Yes | Comma-separated route IDs |

**Method:** POST

### Response Structure

Array of route objects with names, grades, locations, etc.

## Sync Endpoints

The sync endpoints use a different pattern for bidirectional synchronization.

### /syncData?type=todos

Sync user's todo list.

### /syncData?type=ticks

Sync user's tick list.

### /syncData?type=routeRatings

Sync user's route ratings.

### /syncData?type=photoRatings

Sync user's photo ratings.

### /syncData?type=userLocations

Sync user's location data.

### Sync Request Structure

- `since` - The oldest date for which updates should be returned
- `new[]` - List of items to be added (includes app-id string)
- `deleted[]` - List of items to be removed
- `updated[]` - List of items to be updated (includes modified date)

### Sync Response Structure

- `new[]` - List of items added since DATE
- `deleted[]` - List of items deleted since DATE
- `updated[]` - List of items updated since DATE
- `mapping` - {"app-id": server-id} mapping of app IDs to server IDs

## Error Handling

API errors typically return:
- HTTP status codes (200 = success, 4xx = client error, 5xx = server error)
- JSON error messages in the response body

## Rate Limiting

No official rate limits documented, but use reasonable request intervals to avoid throttling.
