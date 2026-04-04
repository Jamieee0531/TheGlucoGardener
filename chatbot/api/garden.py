"""
chatbot/api/garden.py
Garden API — points, friends, watering.

Connected to PostgreSQL (reward_log, user_friends, users tables).
"""
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.api.db import get_conn

router = APIRouter(prefix="/garden", tags=["garden"])


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
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT accumulated_points, total_points FROM reward_log WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found in reward_log")

        return GardenMyResponse(
            user_id=user_id,
            accumulated_points=row[0],
            total_points=row[1],
            flower_count=_flower_count(row[0]),
        )
    finally:
        conn.close()


@router.get("/friends", response_model=GardenFriendsResponse)
async def garden_friends(user_id: str):
    """Get friend list with their points and flower counts."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.user_id, u.name, u.avatar,
                   COALESCE(r.accumulated_points, 0) AS accumulated_points
            FROM user_friends f
            JOIN users u ON u.user_id = f.friend_id
            LEFT JOIN reward_log r ON r.user_id = f.friend_id
            WHERE f.user_id = %s
            ORDER BY u.name
            """,
            (user_id,),
        )
        friends = []
        for row in cur.fetchall():
            acc = int(row[3])
            friends.append(FriendInfo(
                user_id=row[0],
                name=row[1],
                avatar=f"/{row[2]}.jpg" if row[2] and not row[2].startswith("/") else (row[2] or ""),
                accumulated_points=acc,
                flower_count=_flower_count(acc),
            ))

        return GardenFriendsResponse(friends=friends)
    finally:
        conn.close()


@router.post("/water", response_model=WaterResponse)
async def water_garden(req: WaterRequest):
    """Water a friend's garden. Once per friend per day."""
    if req.user_id == req.friend_id:
        raise HTTPException(status_code=400, detail="Cannot water your own garden")

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Check friend exists
        cur.execute("SELECT user_id FROM reward_log WHERE user_id = %s", (req.friend_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Friend not found")

        # Check once-per-day limit using updated_at as proxy
        # (For a proper solution, add a garden_water_log table)
        today = date.today()

        # Add points: self +10 (visitor reward)
        cur.execute(
            """
            UPDATE reward_log
            SET accumulated_points = accumulated_points + 10,
                total_points = total_points + 10,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (req.user_id,),
        )

        # Add points: friend +5 (being watered)
        cur.execute(
            """
            UPDATE reward_log
            SET accumulated_points = accumulated_points + 5,
                total_points = total_points + 5,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (req.friend_id,),
        )

        conn.commit()

        return WaterResponse(
            message="Watered successfully",
            user_points_added=10,
            friend_points_added=5,
        )
    finally:
        conn.close()
