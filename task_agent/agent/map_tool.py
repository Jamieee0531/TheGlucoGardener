import httpx
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from task_agent.utils.math import haversine
from task_agent.config import settings

logger = logging.getLogger(__name__)


async def find_nearby_parks(
    db: AsyncSession,
    lat: float,
    lng: float,
    user_id: str,
    radius_m: int = 2000,
) -> List[Dict[str, Any]]:
    parks: List[Dict[str, Any]] = []

    api_key = settings.google_maps_api_key
    if not api_key or api_key == "dummy_key":
        logger.warning(f"Google Maps API key not set! Fallback for user {user_id}")
    else:
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius_m,
                "type": "park",
                "key": api_key,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
            resp.raise_for_status()

            data = resp.json()
            if data.get("status") == "OK":
                candidates: List[Dict[str, Any]] = []
                unique_coords: set = set()

                for r in data.get("results", []):
                    p_lat = r["geometry"]["location"]["lat"]
                    p_lng = r["geometry"]["location"]["lng"]
                    dist = int(haversine(lat, lng, p_lat, p_lng))
                    coord_key = (round(p_lat, 4), round(p_lng, 4))

                    if dist > 500 and coord_key not in unique_coords:
                        candidates.append({
                            "name": r.get("name", "Nearby park"),
                            "lat": p_lat,
                            "lng": p_lng,
                            "distance_m": dist,
                        })
                        unique_coords.add(coord_key)

                candidates.sort(key=lambda x: abs(x["distance_m"] - 1200))
                parks = candidates[:3]
            else:
                logger.error(
                    f"Google Places API Error: {data.get('status')} - "
                    f"{data.get('error_message', '')}"
                )
        except Exception as e:
            logger.error(f"Google Places API request error for user {user_id}: {e}")

    if not parks:
        if db is not None:
            pl_row = (await db.execute(
                text("SELECT * FROM user_known_places WHERE user_id = :u ORDER BY id LIMIT 1")
                .bindparams(u=user_id)
            )).fetchone()
            if pl_row:
                parks = [{
                    "name": pl_row.place_name,
                    "lat": float(pl_row.gps_lat),
                    "lng": float(pl_row.gps_lng),
                    "distance_m": 0,
                }]

        if not parks:
            logger.warning(f"No places found — using fallback park for {user_id}")
            parks = [{
                "name": "Fallback Park",
                "lat": 1.3521,
                "lng": 103.8198,
                "distance_m": 0,
            }]

    return parks
