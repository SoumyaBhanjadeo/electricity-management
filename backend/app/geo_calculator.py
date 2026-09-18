import math
from typing import List, Dict, Any, Optional

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_geographic_extent(items: List[Any]) -> Optional[Dict[str, float]]:
    if not items:
        return None
    lats = [item.latitude for item in items if getattr(item, "latitude", None) is not None]
    lons = [item.longitude for item in items if getattr(item, "longitude", None) is not None]
    if not lats or not lons:
        return None
    return {
        "min_latitude": round(min(lats), 6),
        "max_latitude": round(max(lats), 6),
        "min_longitude": round(min(lons), 6),
        "max_longitude": round(max(lons), 6)
    }

def build_geojson_feature_collection(equipment_list: List[Any]) -> Dict[str, Any]:
    features = []
    for eq in equipment_list:
        latest_visit = eq.visits[-1] if getattr(eq, "visits", None) and len(eq.visits) > 0 else None
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [eq.longitude, eq.latitude]
            },
            "properties": {
                "asset_id": eq.asset_id,
                "name": eq.name,
                "asset_type": eq.asset_type,
                "elevation_m": eq.elevation_m,
                "status": eq.status,
                "condition_score": latest_visit.condition_score if latest_visit else None,
                "condition_band": latest_visit.condition_band if latest_visit else None,
                "surveyed_on": str(latest_visit.surveyed_on) if latest_visit else None,
                "surveyor": latest_visit.surveyor if latest_visit else None,
                "attribute_json": latest_visit.attribute_json if latest_visit else None,
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }