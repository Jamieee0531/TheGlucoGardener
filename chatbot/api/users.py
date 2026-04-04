"""Users API — profile, exercise patterns, known places, emergency contacts."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.api.db import get_conn

router = APIRouter(prefix="/users", tags=["users"])


# ── Schemas ──────────────────────────────────────────────────────
class UserBasic(BaseModel):
    user_id: str
    name: str
    avatar: str


class UserListResponse(BaseModel):
    users: list[UserBasic]


class UserProfile(BaseModel):
    user_id: str
    name: str
    birth_year: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    waist_cm: float | None = None
    avatar: str | None = None
    language: str | None = None
    onboarding_completed: bool = False


class UserUpdateRequest(BaseModel):
    name: str | None = None
    birth_year: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    waist_cm: float | None = None
    avatar: str | None = None
    language: str | None = None


class ExercisePattern(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    activity_type: str


class ExercisePatternsResponse(BaseModel):
    patterns: list[ExercisePattern]


class KnownPlace(BaseModel):
    place_name: str
    place_type: str
    gps_lat: float | None = None
    gps_lng: float | None = None


class KnownPlacesResponse(BaseModel):
    places: list[KnownPlace]


class EmergencyContact(BaseModel):
    contact_name: str
    phone_number: str
    relationship: str
    notify_on: list[str] = []


class EmergencyContactsResponse(BaseModel):
    contacts: list[EmergencyContact]


# ── User list & profile ──────────────────────────────────────────
@router.get("/list", response_model=UserListResponse)
async def user_list() -> UserListResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, avatar FROM users ORDER BY user_id")
        users = [
            UserBasic(
                user_id=r[0],
                name=r[1],
                avatar=f"/{r[2]}.jpg" if r[2] and not r[2].startswith("/") else (r[2] or ""),
            )
            for r in cur.fetchall()
        ]
        return UserListResponse(users=users)
    finally:
        conn.close()


@router.get("/{user_id}", response_model=UserProfile)
async def user_profile(user_id: str) -> UserProfile:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT user_id, name, birth_year, gender, height_cm, weight_kg,
                      waist_cm, avatar, language, onboarding_completed
               FROM users WHERE user_id = %s""",
            (user_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfile(
            user_id=r[0], name=r[1], birth_year=r[2], gender=r[3],
            height_cm=float(r[4]) if r[4] else None,
            weight_kg=float(r[5]) if r[5] else None,
            waist_cm=float(r[6]) if r[6] else None,
            avatar=f"/{r[7]}.jpg" if r[7] and not r[7].startswith("/") else (r[7] or ""),
            language=r[8], onboarding_completed=r[9] or False,
        )
    finally:
        conn.close()


@router.put("/{user_id}")
async def update_user(user_id: str, req: UserUpdateRequest) -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        fields: list[str] = []
        values: list[object] = []
        for field_name, value in req.model_dump(exclude_none=True).items():
            if field_name == "avatar" and value and value.startswith("/"):
                value = value.replace("/", "").replace(".jpg", "")
            fields.append(f"{field_name} = %s")
            values.append(value)
        if not fields:
            return {"message": "No fields to update"}
        values.append(user_id)
        cur.execute(
            f"UPDATE users SET {', '.join(fields)}, updated_at = NOW() WHERE user_id = %s",
            values,
        )
        conn.commit()
        return {"message": "Updated"}
    finally:
        conn.close()


# ── Exercise patterns ────────────────────────────────────────────
@router.get("/{user_id}/exercise-patterns", response_model=ExercisePatternsResponse)
async def get_exercise_patterns(user_id: str) -> ExercisePatternsResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT day_of_week, start_time, end_time, activity_type
               FROM user_weekly_patterns WHERE user_id = %s ORDER BY day_of_week, start_time""",
            (user_id,),
        )
        patterns = [
            ExercisePattern(
                day_of_week=r[0],
                start_time=r[1].strftime("%H:%M") if hasattr(r[1], "strftime") else str(r[1]),
                end_time=r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2]),
                activity_type=r[3],
            )
            for r in cur.fetchall()
        ]
        return ExercisePatternsResponse(patterns=patterns)
    finally:
        conn.close()


@router.post("/{user_id}/exercise-patterns")
async def save_exercise_patterns(user_id: str, patterns: list[ExercisePattern]) -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_weekly_patterns WHERE user_id = %s", (user_id,))
        for p in patterns:
            cur.execute(
                """INSERT INTO user_weekly_patterns (user_id, day_of_week, start_time, end_time, activity_type)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, p.day_of_week, p.start_time, p.end_time, p.activity_type),
            )
        conn.commit()
        return {"message": "Saved", "count": len(patterns)}
    finally:
        conn.close()


# ── Known places ─────────────────────────────────────────────────
@router.get("/{user_id}/known-places", response_model=KnownPlacesResponse)
async def get_known_places(user_id: str) -> KnownPlacesResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT place_name, place_type, gps_lat, gps_lng FROM user_known_places WHERE user_id = %s",
            (user_id,),
        )
        places = [
            KnownPlace(
                place_name=r[0], place_type=r[1],
                gps_lat=float(r[2]) if r[2] else None,
                gps_lng=float(r[3]) if r[3] else None,
            )
            for r in cur.fetchall()
        ]
        return KnownPlacesResponse(places=places)
    finally:
        conn.close()


@router.post("/{user_id}/known-places")
async def save_known_places(user_id: str, places: list[KnownPlace]) -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_known_places WHERE user_id = %s", (user_id,))
        for p in places:
            cur.execute(
                """INSERT INTO user_known_places (user_id, place_name, place_type, gps_lat, gps_lng)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, p.place_name, p.place_type, p.gps_lat, p.gps_lng),
            )
        conn.commit()
        return {"message": "Saved", "count": len(places)}
    finally:
        conn.close()


# ── Emergency contacts ───────────────────────────────────────────
@router.get("/{user_id}/emergency-contacts", response_model=EmergencyContactsResponse)
async def get_emergency_contacts(user_id: str) -> EmergencyContactsResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT contact_name, phone_number, relationship, notify_on FROM user_emergency_contacts WHERE user_id = %s",
            (user_id,),
        )
        contacts = [
            EmergencyContact(
                contact_name=r[0], phone_number=r[1], relationship=r[2],
                notify_on=r[3] if isinstance(r[3], list) else [],
            )
            for r in cur.fetchall()
        ]
        return EmergencyContactsResponse(contacts=contacts)
    finally:
        conn.close()


@router.post("/{user_id}/emergency-contacts")
async def save_emergency_contacts(user_id: str, contacts: list[EmergencyContact]) -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_emergency_contacts WHERE user_id = %s", (user_id,))
        for c in contacts:
            cur.execute(
                """INSERT INTO user_emergency_contacts (user_id, contact_name, phone_number, relationship, notify_on)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, c.contact_name, c.phone_number, c.relationship, json.dumps(c.notify_on)),
            )
        conn.commit()
        return {"message": "Saved", "count": len(contacts)}
    finally:
        conn.close()
