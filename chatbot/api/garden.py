"""
chatbot/api/garden.py
Garden API — points, friends, watering.

Mock data for now; swap to PostgreSQL queries when DB is ready.
"""
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/garden", tags=["garden"])


# ── Mock data (replace with DB queries later) ────────────────────
_MOCK_POINTS = {
    "user_001": {"accumulated_points": 2400, "total_points": 2400},
    "user_002": {"accumulated_points": 800, "total_points": 800},
    "user_003": {"accumulated_points": 350, "total_points": 350},
}

_MOCK_FRIENDS = {
    "user_001": ["user_002", "user_003"],
    "user_002": ["user_001", "user_003"],
    "user_003": ["user_001", "user_002"],
}

_MOCK_USERS = {
    "user_001": {"name": "Alice", "avatar": "/avatars/avatar.jpg"},
    "user_002": {"name": "Bob", "avatar": "/avatars/avatar3.jpg"},
    "user_003": {"name": "Charlie", "avatar": "/avatars/avatar1.jpg"},
}

# Track watering: {(user_id, friend_id): date}
_water_log: dict[tuple[str, str], date] = {}


# ── Response schemas ─────────────────────────────────────────────
class GardenMyResponse(BaseModel):
    user_id: str
    accumulated_points: int
    total_points: int
    flower_count: int


class FriendInfo(BaseModel):
    user_id: str
    name: str
    avatar: str
    accumulated_points: int
    flower_count: int


class GardenFriendsResponse(BaseModel):
    friends: list[FriendInfo]


class WaterRequest(BaseModel):
    user_id: str
    friend_id: str


class WaterResponse(BaseModel):
    message: str
    user_points_added: int
    friend_points_added: int


# ── Helper ───────────────────────────────────────────────────────
def _flower_count(accumulated_points: int) -> int:
    return min(accumulated_points // 500, 25)


# ── Endpoints ────────────────────────────────────────────────────
@router.get("/my", response_model=GardenMyResponse)
async def garden_my(user_id: str):
    """Get current user's points and flower count."""
    points = _MOCK_POINTS.get(user_id)
    if not points:
        raise HTTPException(status_code=404, detail="User not found")

    return GardenMyResponse(
        user_id=user_id,
        accumulated_points=points["accumulated_points"],
        total_points=points["total_points"],
        flower_count=_flower_count(points["accumulated_points"]),
    )


@router.get("/friends", response_model=GardenFriendsResponse)
async def garden_friends(user_id: str):
    """Get friend list with their points and flower counts."""
    friend_ids = _MOCK_FRIENDS.get(user_id, [])
    friends = []
    for fid in friend_ids:
        user_info = _MOCK_USERS.get(fid, {})
        points = _MOCK_POINTS.get(fid, {})
        acc = points.get("accumulated_points", 0)
        friends.append(FriendInfo(
            user_id=fid,
            name=user_info.get("name", "Unknown"),
            avatar=user_info.get("avatar", ""),
            accumulated_points=acc,
            flower_count=_flower_count(acc),
        ))

    return GardenFriendsResponse(friends=friends)


@router.post("/water", response_model=WaterResponse)
async def water_garden(req: WaterRequest):
    """Water a friend's garden. Once per friend per day."""
    if req.user_id == req.friend_id:
        raise HTTPException(status_code=400, detail="Cannot water your own garden")

    if req.friend_id not in _MOCK_POINTS:
        raise HTTPException(status_code=404, detail="Friend not found")

    # Check once-per-day limit
    today = date.today()
    key = (req.user_id, req.friend_id)
    if _water_log.get(key) == today:
        raise HTTPException(
            status_code=429,
            detail="Already watered this friend today",
        )

    # Add points: friend +10, self +5
    friend_pts = _MOCK_POINTS[req.friend_id]
    friend_pts["accumulated_points"] += 10
    friend_pts["total_points"] += 10

    if req.user_id in _MOCK_POINTS:
        self_pts = _MOCK_POINTS[req.user_id]
        self_pts["accumulated_points"] += 5
        self_pts["total_points"] += 5

    # Record watering
    _water_log[key] = today

    return WaterResponse(
        message="Watered successfully",
        user_points_added=5,
        friend_points_added=10,
    )
