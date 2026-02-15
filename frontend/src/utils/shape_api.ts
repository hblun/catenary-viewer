import type { Feature, FeatureCollection, Geometry } from 'geojson';

export interface ShapeOptions {
	min_x?: number;
	min_y?: number;
	max_x?: number;
	max_y?: number;
	simplify?: number;
	format?: 'geojson' | 'polyline';
}

export interface ShapeRequestItem {
	chateau: string;
	shape_ids: string[];
}

const SHAPE_API_BASE = 'https://birchshapescustom.catenarymaps.org/get_shapes';

/**
 * Batch fetches shapes from the backend.
 * Groups items by chateau automatically, but backend anticipates a list of {chateau, shape_ids} items.
 *
 * @param items List of shape requests (chateau + shape_id)
 * @param options Query options (simplification, bbox, format)
 * @returns A map of shape_id -> Geometry (or Feature/Polyline depending on format, but effectively we normalize to logic used by components)
 */
export async function batchFetchShapes(
	items: { chateau: string; shape_id: string }[],
	options: ShapeOptions = {}
): Promise<Record<string, any>> {
	if (items.length === 0) return {};

	// 1. Group by chateau to match backend expected structure: Vec<ShapeRequestItem>
	const grouped: Record<string, string[]> = {};
	for (const item of items) {
		if (!grouped[item.chateau]) {
			grouped[item.chateau] = [];
		}
		grouped[item.chateau].push(item.shape_id);
	}

	const requestBody: ShapeRequestItem[] = Object.entries(grouped).map(([chateau, ids]) => ({
		chateau,
		shape_ids: ids
	}));

	// 2. Build Query String for Options
	const queryParams = new URLSearchParams();
	if (options.min_x !== undefined) queryParams.set('min_x', String(options.min_x));
	if (options.min_y !== undefined) queryParams.set('min_y', String(options.min_y));
	if (options.max_x !== undefined) queryParams.set('max_x', String(options.max_x));
	if (options.max_y !== undefined) queryParams.set('max_y', String(options.max_y));
	if (options.simplify !== undefined) queryParams.set('simplify', String(options.simplify));
	if (options.format) queryParams.set('format', options.format);
	else queryParams.set('format', 'geojson'); // default

	const url = `${SHAPE_API_BASE}?${queryParams.toString()}`;

	try {
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(requestBody)
		});

		if (!response.ok) {
			throw new Error(`Shape fetch failed: ${response.statusText}`);
		}

		const data = await response.json();
		const resultMap: Record<string, any> = {};

		// 3. Parse Response
		// Internal Format matches:
		// Polyline: Array<{ chateau, shape_id, polyline }>
		// GeoJSON: FeatureCollection w/ Features. Each Feature has properties { chateau, shape_id }

		const isPolyline = options.format === 'polyline';

		if (isPolyline) {
			// Expect Array or Object? User request says: json(polyline_results) which is Vec<Value>
			if (Array.isArray(data)) {
				for (const item of data) {
					if (item.shape_id && item.polyline) {
						resultMap[item.shape_id] = item; // Store the whole object or just polyline? Components might expect specific fmt.
						// RouteScreen expects: { type: 'LineString', coordinates: ... } OR raw polyline string if we handle it?
						// StopScreen expects: existing logic handles polyline decoding OR geojson.
						// Let's stick to returning what the backend returns, and let component handle or normalize here.
						// Actually, standardizing on GeoJSON (Geometry) is easiest for components unless they specifically asked for polyline.
					}
				}
			}
		} else {
			// GeoJSON FeatureCollection
			if (data.type === 'FeatureCollection' && Array.isArray(data.features)) {
				for (const feature of data.features) {
					const props = feature.properties || {};
					const shapeIds = props.shape_id; // Could be string
					// Note: Backend code: properties: Some(serde_json::Map::from_iter(vec![("chateau", ...), ("shape_id", ...)]))
					if (shapeIds) {
						// We map by shape_id.
						// Ideally we return the Geometry or the Feature?
						// StopScreen expects `fetched_shapes_cache[shape_id] = json.geometry || json` (Feature or Geometry)
						resultMap[shapeIds] = feature;
					}
				}
			}
		}

		return resultMap;
	} catch (e) {
		console.error('Batch shape fetch error:', e);
		return {};
	}
}
