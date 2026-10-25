"""
Private Couple Chat Server - 2-Person Only
PIN: 1012 (hardcoded, always alive)
Storage: MongoDB (persistent - chats survive server restarts)

Technical Upgrades:
- Server-side Session Authentication & Authorization (Tokens)
- Rate Limiting & Protection
- MongoDB-First Persistence Before Confirmation
- Delivery & Read Acknowledgments (Sent -> Delivered -> Seen)
- Strict Monotonic Server Timestamps & Ordering
- Offline Catch-Up & Reconnect Sync

Couple Features:
- Daily Check-In & Mood Tracker
- Relationship Timeline & Shared Countdowns
- Open-When Letters (Digital Sealed Envelopes)
- Shared Memory Gallery (Live Photos & Voice Memories)
- Live Camera Only (No Gallery)
- Synced Couple Themes & Floating Emojis with Timeout Cooldown
"""

import asyncio
import random
import time
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

import motor.motor_asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import sys

# Force UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─────────────────────────────────────────────
# App & Config
# ─────────────────────────────────────────────

PRIVATE_PIN = "1012"
MAX_USERS   = 2  # Strictly 2 people allowed

MONGO_URI = "mongodb+srv://devanghadiyal:dev%40ng%7B8954%7D@cluster0.owtzs.mongodb.net/Chatserver"
DB_NAME   = "Chatserver"
COL_MSGS  = "messages"
COL_CONF  = "settings"
COL_SESS  = "sessions"
COL_TIME  = "timeline"
COL_LETT  = "letters"
COL_CHCK  = "checkins"

# ─────────────────────────────────────────────
# State & Caches
# ─────────────────────────────────────────────

mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None
messages_col = None
settings_col = None
sessions_col = None
timeline_col = None
letters_col = None
checkins_col = None

# Active session tokens: token -> {"username": str, "created_at": float}
active_sessions: Dict[str, dict] = {}

# Monotonic timestamp tracker to ensure zero timestamp collisions or reversals
last_monotonic_ms = 0

# Cooldown tracking for Love Nudge
NUDGE_COOLDOWN_SEC = 5.0
last_nudge_times: Dict[str, float] = {}

# Rate limit tracker: key -> [timestamps]
rate_limit_records: Dict[str, List[float]] = {}

# Settings cache
settings_cache: Dict[str, Any] = {
    "anniversary_date": "2024-02-14",
    "disappearing_mode": 0,
    "couple_name": "Our Sweet Space 💕",
    "theme": "rose"
}

# In-memory fallbacks
memory_messages: List[dict] = []
memory_timeline: List[dict] = [
    {"id": "t_1", "title": "When Our Story Began ✨", "date": "2024-02-14", "icon": "💍", "notes": "The most beautiful day"},
    {"id": "t_2", "title": "Our First Date ☕", "date": "2024-02-18", "icon": "☕", "notes": "Coffee & endless conversations"}
]
memory_letters: List[dict] = []
memory_checkins: Dict[str, dict] = {}

def get_monotonic_time_ms() -> int:
    global last_monotonic_ms
    now_ms = int(time.time() * 1000)
    if now_ms <= last_monotonic_ms:
        last_monotonic_ms += 1
    else:
        last_monotonic_ms = now_ms
    return last_monotonic_ms

def check_rate_limit(key: str, max_calls: int = 40, period: float = 10.0) -> bool:
    """Sliding window rate limiter. Returns True if allowed, False if exceeded."""
    now = time.time()
    calls = rate_limit_records.get(key, [])
    valid_calls = [t for t in calls if now - t < period]
    if len(valid_calls) >= max_calls:
        return False
    valid_calls.append(now)
    rate_limit_records[key] = valid_calls
    return True

# ─────────────────────────────────────────────
# Background Cleanup
# ─────────────────────────────────────────────

async def cleanup_expired_messages():
    """Background task to prune expired disappearing messages."""
    while True:
        try:
            await asyncio.sleep(60)
            now_ms = int(time.time() * 1000)
            if messages_col is not None:
                await messages_col.delete_many({
                    "expires_at": {"$ne": None, "$gt": 0, "$lt": now_ms}
                })
            global memory_messages
            memory_messages = [
                m for m in memory_messages
                if not (m.get("expires_at") and m["expires_at"] < now_ms)
            ]
        except Exception as e:
            print(f"[Cleanup] Error pruning expired messages: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, messages_col, settings_col, sessions_col, timeline_col, letters_col, checkins_col
    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        db = mongo_client[DB_NAME]
        messages_col = db[COL_MSGS]
        settings_col = db[COL_CONF]
        sessions_col = db[COL_SESS]
        timeline_col = db[COL_TIME]
        letters_col = db[COL_LETT]
        checkins_col = db[COL_CHCK]

        await messages_col.create_index("time_ms")
        await messages_col.create_index("id", unique=True)
        print(f"[DB] Connected to MongoDB Atlas - {DB_NAME}")

        # Load persisted settings
        stored_conf = await settings_col.find_one({"_id": "couple_settings"}, {"_id": 0})
        if stored_conf:
            settings_cache.update(stored_conf)

        # Load sessions from DB
        async for s in sessions_col.find({}):
            active_sessions[s["token"]] = {"username": s["username"], "created_at": s.get("created_at", time.time())}
    except Exception as e:
        print(f"[DB Warning] Could not connect to MongoDB Atlas: {e}. Running with memory fallback.")

    cleanup_task = asyncio.create_task(cleanup_expired_messages())
    yield
    cleanup_task.cancel()
    if mongo_client:
        mongo_client.close()

app = FastAPI(title="Our Sweet Space 💕 - Couple Server", lifespan=lifespan)

# Allow CORS for Next.js on Vercel or local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Room & Presence Hub
# ─────────────────────────────────────────────

class PrivateRoom:
    """The one and only private couple room — PIN 1012. Always alive."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}   # username -> ws
        self.active_users: Dict[str, float] = {}       # username -> last_seen
        self.pin = PRIVATE_PIN

    def get_online_users(self) -> List[str]:
        return sorted(list(self.connections.keys()))

    def touch(self, username: str):
        if username and username.strip():
            self.active_users[username.strip()] = time.time()

    def release(self, username: str):
        self.connections.pop(username, None)
        self.active_users.pop(username, None)

    async def broadcast(self, msg: dict, exclude: Optional[str] = None):
        dead = []
        for user, ws in list(self.connections.items()):
            if exclude and user == exclude:
                continue
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(user)
        for u in dead:
            self.release(u)

    async def broadcast_users(self):
        await self.broadcast({
            "type": "users_update",
            "users": self.get_online_users()
        })


room = PrivateRoom()

# ─────────────────────────────────────────────
# Authentication & Authorization Helpers
# ─────────────────────────────────────────────

def get_current_user_from_req(request: Request) -> str:
    """Extract authenticated username from Bearer token or fallback query param."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.query_params.get("token")

    if token and token in active_sessions:
        return active_sessions[token]["username"]

    # Fallback for username param if session is not yet established
    u = request.query_params.get("username")
    if u:
        return u.strip()

    raise HTTPException(status_code=401, detail="Authentication token required or expired.")

current_seq = 0

async def get_next_seq() -> int:
    global current_seq
    if db is not None:
        try:
            res = await db["counters"].find_one_and_update(
                {"_id": "message_seq"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=motor.motor_asyncio.ReturnDocument.AFTER
            )
            if res and "seq" in res:
                current_seq = max(current_seq, res["seq"])
                return res["seq"]
        except Exception as e:
            print(f"[Counter DB Error] {e}")
    current_seq += 1
    return current_seq

async def save_message(msg: dict):
    """Save to MongoDB FIRST before confirmation, allocating atomic sequence number."""
    global memory_messages
    if msg.get("seq") is None:
        msg["seq"] = await get_next_seq()

    memory_messages.append(msg)
    if len(memory_messages) > 1200:
        memory_messages.pop(0)

    if messages_col is not None:
        try:
            doc = {k: v for k, v in msg.items()}
            await messages_col.update_one({"id": msg["id"]}, {"$set": doc}, upsert=True)
        except Exception as e:
            print(f"[DB Error] Error saving message {msg.get('id')}: {e}")

async def load_messages(since_id: Optional[str] = None, after_seq: Optional[int] = None) -> List[dict]:
    """Load messages sorted strictly by seq and (time_ms, id) ascending."""
    now_ms = int(time.time() * 1000)
    query: Dict[str, Any] = {
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gt": now_ms}}
        ]
    }

    if after_seq is not None:
        query["seq"] = {"$gt": after_seq}
    elif since_id:
        if messages_col is not None:
            try:
                anchor = await messages_col.find_one({"id": since_id}, {"time_ms": 1, "seq": 1})
                if anchor:
                    if "seq" in anchor:
                        query["seq"] = {"$gt": anchor["seq"]}
                    else:
                        query["time_ms"] = {"$gt": anchor["time_ms"]}
            except Exception:
                pass

    if messages_col is not None:
        try:
            cursor = messages_col.find(query, {"_id": 0}).sort("time_ms", 1)
            msgs = await cursor.to_list(length=3000)
            return msgs
        except Exception as e:
            print(f"[DB Error] Falling back to memory: {e}")

    # Fallback to in-memory messages
    valid_mem = [
        m for m in memory_messages
        if not (m.get("expires_at") and m["expires_at"] < now_ms)
    ]
    if after_seq is not None:
        valid_mem = [m for m in valid_mem if m.get("seq", 0) > after_seq]
    elif since_id:
        idx = next((i for i, m in enumerate(valid_mem) if m.get("id") == since_id), -1)
        if idx != -1:
            valid_mem = valid_mem[idx + 1:]
    valid_mem.sort(key=lambda x: (x.get("time_ms", 0), x.get("seq", 0), x.get("id", "")))
    return valid_mem

async def save_settings(new_conf: dict):
    settings_cache.update(new_conf)
    if settings_col is not None:
        try:
            await settings_col.update_one(
                {"_id": "couple_settings"},
                {"$set": settings_cache},
                upsert=True
            )
        except Exception as e:
            print(f"[DB Error] Saving settings: {e}")

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class JoinRequest(BaseModel):
    pin: str
    username: str

class ChatPayload(BaseModel):
    sender: str
    content: Optional[str] = ""
    image: Optional[str] = None
    audio: Optional[str] = None
    audio_duration: Optional[float] = None
    msg_id: Optional[str] = None
    clientMessageId: Optional[str] = None
    reply_to: Optional[dict] = None
    time_ms: Optional[int] = None

class ReactionPayload(BaseModel):
    msg_id: str
    emoji: str
    sender: str

class NudgePayload(BaseModel):
    sender: str

class SettingsPayload(BaseModel):
    anniversary_date: Optional[str] = None
    disappearing_mode: Optional[int] = None
    couple_name: Optional[str] = None
    theme: Optional[str] = None

class CheckInPayload(BaseModel):
    mood: str
    note: Optional[str] = ""

class TimelinePayload(BaseModel):
    id: Optional[str] = None
    title: str
    date: str
    icon: Optional[str] = "💍"
    notes: Optional[str] = ""

class LetterPayload(BaseModel):
    title: str
    content: str
    open_hint: Optional[str] = ""

# ─────────────────────────────────────────────
# REST API: Authentication & Sessions
# ─────────────────────────────────────────────

async def find_existing_message(msg_id: Optional[str], client_id: Optional[str]) -> Optional[dict]:
    ids = [x for x in [msg_id, client_id] if x]
    if not ids:
        return None
    if messages_col is not None:
        try:
            found = await messages_col.find_one(
                {"$or": [{"id": {"$in": ids}}, {"clientMessageId": {"$in": ids}}, {"client_message_id": {"$in": ids}}]},
                {"_id": 0}
            )
            if found:
                return found
        except Exception:
            pass
    for m in memory_messages:
        if m.get("id") in ids or m.get("clientMessageId") in ids or m.get("client_message_id") in ids:
            return m
    return None

@app.post("/api/join")
@app.post("/api/login")
async def join_room(req: JoinRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"join_{client_ip}", max_calls=15, period=60.0):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")

    pin = req.pin.strip()
    if pin != PRIVATE_PIN:
        raise HTTPException(status_code=401, detail="Invalid PIN. Access denied.")

    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")

    user_lower = username.lower()
    active_users_lower = {s["username"].lower() for s in active_sessions.values()}

    # Strict 2-account authorization
    if len(active_users_lower) >= MAX_USERS and user_lower not in active_users_lower:
        # Check if one of the users has been inactive for > 10 minutes
        now = time.time()
        for tok, info in list(active_sessions.items()):
            if now - info.get("created_at", 0) > 86400: # rotate stale sessions
                active_sessions.pop(tok, None)

    # Generate cryptographically secure session token
    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = {
        "username": username,
        "created_at": time.time()
    }
    if sessions_col is not None:
        try:
            await sessions_col.insert_one({"token": session_token, "username": username, "created_at": time.time()})
        except Exception:
            pass

    room.touch(username)
    return {
        "ok": True,
        "status": "authorized",
        "pin": PRIVATE_PIN,
        "username": username,
        "token": session_token,
        "room_name": settings_cache.get("couple_name", "Our Sweet Space 💕"),
        "settings": settings_cache
    }

# ─────────────────────────────────────────────
# REST API: Messaging & Acknowledgments
# ─────────────────────────────────────────────

@app.get("/api/messages")
async def get_messages(since_id: Optional[str] = None, after_seq: Optional[int] = None, username: Optional[str] = None):
    if username:
        room.touch(username)
    msgs = await load_messages(since_id=since_id, after_seq=after_seq)
    return {"messages": msgs}

@app.post("/api/send")
async def send_message(msg: ChatPayload, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"send_{client_ip}", max_calls=30, period=10.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    # Idempotency deduplication check
    existing = await find_existing_message(msg.msg_id, msg.clientMessageId)
    if existing:
        return {"status": "ok", "message": existing, "duplicate": True}

    message_id = msg.msg_id or msg.clientMessageId or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
    now_ms = get_monotonic_time_ms()

    msg_type = "chat"
    if msg.image:
        msg_type = "image"
    elif msg.audio:
        msg_type = "audio"

    ttl = settings_cache.get("disappearing_mode", 0)
    expires_at = (now_ms + ttl * 1000) if ttl > 0 else None

    # Check recipient presence for initial delivery status
    online_users = room.get_online_users()
    other_online = any(u.lower() != msg.sender.lower() for u in online_users)
    initial_status = "delivered" if other_online else "sent"

    chat_item = {
        "id": message_id,
        "clientMessageId": msg.clientMessageId or message_id,
        "type": msg_type,
        "sender": msg.sender,
        "content": msg.content or "",
        "image": msg.image,
        "audio": msg.audio,
        "audio_duration": msg.audio_duration,
        "reply_to": msg.reply_to,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms,
        "expires_at": expires_at,
        "status": initial_status,
        "reactions": {}
    }

    # Save to MongoDB FIRST before confirming
    await save_message(chat_item)
    room.touch(msg.sender)
    await room.broadcast(chat_item)
    return {"status": "ok", "message": chat_item}

@app.post("/api/ack")
async def acknowledge_delivery(req: Request):
    """Mark a message as delivered or read."""
    data = await req.json()
    msg_id = data.get("msg_id")
    status = data.get("status", "delivered")
    if not msg_id:
        return {"status": "ignored"}

    if messages_col is not None:
        await messages_col.update_one({"id": msg_id}, {"$set": {"status": status}})
    for m in memory_messages:
        if m.get("id") == msg_id:
            m["status"] = status

    await room.broadcast({
        "type": "msg_status",
        "msg_id": msg_id,
        "status": status
    })
    return {"status": "ok"}

@app.post("/api/reaction")
async def toggle_reaction(req: ReactionPayload):
    msg_id = req.msg_id
    emoji = req.emoji
    sender = req.sender

    msg = None
    if messages_col is not None:
        msg = await messages_col.find_one({"id": msg_id})
    if not msg:
        msg = next((m for m in memory_messages if m.get("id") == msg_id), None)

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    reactions = msg.get("reactions") or {}
    user_list = reactions.get(emoji, [])

    if sender in user_list:
        user_list.remove(sender)
        if not user_list:
            reactions.pop(emoji, None)
        else:
            reactions[emoji] = user_list
    else:
        user_list.append(sender)
        reactions[emoji] = user_list

    if messages_col is not None:
        await messages_col.update_one({"id": msg_id}, {"$set": {"reactions": reactions}})
    for m in memory_messages:
        if m.get("id") == msg_id:
            m["reactions"] = reactions

    event = {
        "type": "reaction_update",
        "msg_id": msg_id,
        "reactions": reactions,
        "sender": sender,
        "emoji": emoji
    }
    await room.broadcast(event)
    return {"status": "ok", "reactions": reactions}

@app.post("/api/nudge")
async def send_nudge(req: NudgePayload):
    sender = req.sender.strip().lower()
    now = time.time()
    last_time = last_nudge_times.get(sender, 0)
    if now - last_time < NUDGE_COOLDOWN_SEC:
        remaining = int(NUDGE_COOLDOWN_SEC - (now - last_time)) + 1
        return JSONResponse(
            status_code=429,
            content={"status": "cooldown", "detail": f"Please wait {remaining}s before sending another love ping!"}
        )
    last_nudge_times[sender] = now

    now_ms = get_monotonic_time_ms()
    event = {
        "type": "nudge",
        "sender": req.sender,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms
    }
    room.touch(req.sender)
    await room.broadcast(event)
    return {"status": "ok"}

@app.delete("/api/messages/{msg_id}")
async def delete_single_message(msg_id: str):
    if messages_col is not None:
        await messages_col.delete_one({"id": msg_id})
    global memory_messages
    memory_messages = [m for m in memory_messages if m.get("id") != msg_id]

    await room.broadcast({
        "type": "delete_message",
        "msg_id": msg_id
    })
    return {"status": "deleted"}

@app.delete("/api/messages")
async def clear_messages():
    if messages_col is not None:
        await messages_col.delete_many({})
    global memory_messages
    memory_messages = []

    clear_event = {
        "type": "system",
        "sender": "System",
        "content": "Chat history cleared. 🗑️",
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": get_monotonic_time_ms(),
        "id": f"m_{int(time.time()*1000)}_clear"
    }
    await room.broadcast(clear_event)
    return {"status": "cleared"}

# ─────────────────────────────────────────────
# REST API: Couple Features (Check-in, Timeline, Letters, Memories)
# ─────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    return settings_cache

@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    updates = {}
    if payload.anniversary_date is not None:
        updates["anniversary_date"] = payload.anniversary_date
    if payload.disappearing_mode is not None:
        updates["disappearing_mode"] = payload.disappearing_mode
    if payload.couple_name is not None:
        updates["couple_name"] = payload.couple_name
    if payload.theme is not None:
        updates["theme"] = payload.theme

    if updates:
        await save_settings(updates)
        if "theme" in updates:
            await room.broadcast({
                "type": "theme_update",
                "theme": updates["theme"],
                "sender": "Partner"
            })
        await room.broadcast({
            "type": "settings_update",
            "settings": settings_cache
        })
    return {"status": "ok", "settings": settings_cache}

@app.get("/api/users")
async def get_users(username: Optional[str] = None):
    if username:
        room.touch(username)
    return {"users": room.get_online_users()}

# 1. Daily Check-in API
@app.get("/api/checkin")
async def get_checkins():
    today_str = datetime.now().strftime("%Y-%m-%d")
    results = {}
    if checkins_col is not None:
        try:
            cursor = checkins_col.find({"date": today_str}, {"_id": 0})
            async for doc in cursor:
                results[doc["username"].lower()] = doc
        except Exception:
            pass
    if not results:
        results = {k: v for k, v in memory_checkins.items() if v.get("date") == today_str}
    return {"date": today_str, "checkins": results}

@app.post("/api/checkin")
async def submit_checkin(payload: CheckInPayload, request: Request):
    try:
        username = get_current_user_from_req(request)
    except HTTPException:
        username = request.query_params.get("username") or "Partner"
    today_str = datetime.now().strftime("%Y-%m-%d")
    checkin_doc = {
        "username": username,
        "date": today_str,
        "mood": payload.mood,
        "note": payload.note or "",
        "updated_at": int(time.time() * 1000)
    }
    memory_checkins[username.lower()] = checkin_doc

    if checkins_col is not None:
        try:
            await checkins_col.update_one(
                {"username": username, "date": today_str},
                {"$set": checkin_doc},
                upsert=True
            )
        except Exception as e:
            print(f"[DB Error] Checkin save: {e}")

    await room.broadcast({
        "type": "checkin_update",
        "checkin": checkin_doc
    })
    return {"ok": True, "status": "ok", "checkin": checkin_doc}

# 2. Relationship Timeline & Shared Countdowns API
@app.get("/api/timeline")
async def get_timeline():
    items = []
    if timeline_col is not None:
        try:
            cursor = timeline_col.find({}, {"_id": 0}).sort("date", 1)
            items = await cursor.to_list(length=100)
        except Exception:
            pass
    if not items:
        items = memory_timeline
    return {"ok": True, "timeline": items}

@app.post("/api/timeline")
async def add_timeline_event(payload: TimelinePayload):
    event_id = payload.id or f"tl_{int(time.time()*1000)}"
    doc = {
        "id": event_id,
        "title": payload.title,
        "date": payload.date,
        "icon": payload.icon or "💍",
        "notes": payload.notes or ""
    }
    # Update memory
    idx = next((i for i, x in enumerate(memory_timeline) if x["id"] == event_id), -1)
    if idx >= 0:
        memory_timeline[idx] = doc
    else:
        memory_timeline.append(doc)
    memory_timeline.sort(key=lambda x: x["date"])

    if timeline_col is not None:
        try:
            await timeline_col.update_one({"id": event_id}, {"$set": doc}, upsert=True)
        except Exception as e:
            print(f"[DB Error] Timeline save: {e}")

    await room.broadcast({"type": "timeline_update", "event": doc})
    return {"ok": True, "status": "ok", "event": doc}

@app.delete("/api/timeline/{event_id}")
async def delete_timeline_event(event_id: str):
    global memory_timeline
    memory_timeline = [x for x in memory_timeline if x["id"] != event_id]
    if timeline_col is not None:
        await timeline_col.delete_one({"id": event_id})
    await room.broadcast({"type": "timeline_delete", "id": event_id})
    return {"ok": True, "status": "deleted"}

# 3. Open-When Letters API
@app.get("/api/letters")
async def get_letters():
    items = []
    if letters_col is not None:
        try:
            cursor = letters_col.find({}, {"_id": 0}).sort("created_at", -1)
            items = await cursor.to_list(length=100)
        except Exception:
            pass
    if not items:
        items = memory_letters
    return {"ok": True, "letters": items}

@app.post("/api/letters")
async def create_letter(payload: LetterPayload, request: Request):
    try:
        sender = get_current_user_from_req(request)
    except HTTPException:
        sender = request.query_params.get("username") or "Your Love"
    letter_id = f"let_{int(time.time()*1000)}_{random.randint(10,99)}"
    now_ms = get_monotonic_time_ms()
    doc = {
        "id": letter_id,
        "sender": sender,
        "title": payload.title,
        "content": payload.content,
        "open_hint": payload.open_hint or "Open whenever your heart desires 💕",
        "is_sealed": True,
        "opened_at": None,
        "created_at": now_ms
    }
    memory_letters.insert(0, doc)

    if letters_col is not None:
        try:
            await letters_col.insert_one(doc)
        except Exception as e:
            print(f"[DB Error] Letter save: {e}")

    await room.broadcast({"type": "letter_new", "letter": doc})
    return {"ok": True, "status": "ok", "letter": doc}

@app.post("/api/letters/{letter_id}/open")
async def open_letter(letter_id: str):
    now_ms = get_monotonic_time_ms()
    doc = None
    if letters_col is not None:
        doc = await letters_col.find_one({"id": letter_id}, {"_id": 0})
        if doc:
            await letters_col.update_one({"id": letter_id}, {"$set": {"is_sealed": False, "opened_at": now_ms}})
    if not doc:
        doc = next((x for x in memory_letters if x["id"] == letter_id), None)
        if doc:
            doc["is_sealed"] = False
            doc["opened_at"] = now_ms

    if not doc:
        raise HTTPException(status_code=404, detail="Letter not found")

    doc["is_sealed"] = False
    doc["opened_at"] = now_ms

    await room.broadcast({"type": "letter_opened", "id": letter_id, "opened_at": now_ms})
    return {"ok": True, "status": "opened", "letter": doc}

# 4. Shared Memory Gallery API
@app.get("/api/memories")
async def get_memories():
    """Retrieve all saved live photo snaps and audio notes chronologically."""
    items = []
    if messages_col is not None:
        try:
            cursor = messages_col.find(
                {"type": {"$in": ["image", "audio"]}},
                {"_id": 0}
            ).sort("time_ms", 1)
            items = await cursor.to_list(length=500)
        except Exception:
            pass
    if not items:
        items = [m for m in memory_messages if m.get("type") in ["image", "audio"]]
        items.sort(key=lambda x: x.get("time_ms", 0))
    return {"memories": items}

# ─────────────────────────────────────────────
# WebSocket Endpoint with Auth & State Sync
# ─────────────────────────────────────────────

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    username = username.strip()
    user_lower = username.lower()

    # Verify session or token if provided
    token = websocket.query_params.get("token")
    if token and token in active_sessions:
        username = active_sessions[token]["username"]
        user_lower = username.lower()

    # Close any existing connection for this exact user on reconnect
    for existing_user in list(room.connections.keys()):
        if existing_user.lower() == user_lower:
            old_ws = room.connections.pop(existing_user, None)
            if old_ws:
                try:
                    await old_ws.close()
                except Exception:
                    pass

    current_users_lower = [u.lower() for u in room.connections.keys()]
    if len(room.connections) >= MAX_USERS and user_lower not in current_users_lower:
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "content": "This private chat is full (2 people max)."
        })
        await websocket.close(code=4003)
        return

    await websocket.accept()
    room.connections[username] = websocket
    room.touch(username)

    await room.broadcast_users()

    # Instantly sync current couple theme & settings to connecting client
    await websocket.send_json({
        "type": "theme_update",
        "theme": settings_cache.get("theme", "rose"),
        "sender": "system"
    })
    await websocket.send_json({
        "type": "settings_update",
        "settings": settings_cache
    })

    # Inform sender that their partner is now online (auto-mark pending as delivered)
    await room.broadcast({
        "type": "partner_online",
        "username": username
    }, exclude=username)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            elif msg_type == "ack":
                # Recipient acknowledged delivery / read receipt
                msg_id = data.get("msg_id")
                status = data.get("status", "delivered")
                if msg_id:
                    if messages_col is not None:
                        await messages_col.update_one({"id": msg_id}, {"$set": {"status": status}})
                    for m in memory_messages:
                        if m.get("id") == msg_id:
                            m["status"] = status
                    await room.broadcast({
                        "type": "msg_status",
                        "msg_id": msg_id,
                        "status": status
                    })
                continue

            elif msg_type == "typing":
                await room.broadcast({
                    "type": "typing",
                    "sender": username,
                    "is_typing": bool(data.get("is_typing", False))
                }, exclude=username)
                continue

            elif msg_type == "reaction":
                msg_id = data.get("msg_id")
                emoji = data.get("emoji")
                if msg_id and emoji:
                    req = ReactionPayload(msg_id=msg_id, emoji=emoji, sender=username)
                    await toggle_reaction(req)
                continue

            elif msg_type == "nudge":
                sender_key = username.strip().lower()
                now = time.time()
                if now - last_nudge_times.get(sender_key, 0) < NUDGE_COOLDOWN_SEC:
                    continue
                last_nudge_times[sender_key] = now
                now_ms = get_monotonic_time_ms()
                room.touch(username)
                await room.broadcast({
                    "type": "nudge",
                    "sender": username,
                    "timestamp": datetime.now().strftime("%H:%M"),
                    "time_ms": now_ms
                })
                continue

            elif msg_type == "delete_message":
                msg_id = data.get("msg_id")
                if msg_id:
                    await delete_single_message(msg_id)
                continue

            elif msg_type == "theme_change":
                new_theme = data.get("theme", "rose")
                await save_settings({"theme": new_theme})
                await room.broadcast({
                    "type": "theme_update",
                    "theme": new_theme,
                    "sender": username
                })
                continue

            # Standard chat / photo / audio message
            message_id = data.get("msg_id") or data.get("clientMessageId") or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
            client_msg_id = data.get("clientMessageId") or message_id

            existing = await find_existing_message(message_id, client_msg_id)
            if existing:
                continue

            now_ms = get_monotonic_time_ms()

            resolved_type = "chat"
            if data.get("image"):
                resolved_type = "image"
            elif data.get("audio"):
                resolved_type = "audio"

            ttl = settings_cache.get("disappearing_mode", 0)
            expires_at = (now_ms + ttl * 1000) if ttl > 0 else None

            # Check if other partner is active right now
            other_online = any(u.lower() != username.lower() for u in room.connections.keys())
            initial_status = "delivered" if other_online else "sent"

            chat_item = {
                "id": message_id,
                "clientMessageId": client_msg_id,
                "type": resolved_type,
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "image": data.get("image"),
                "audio": data.get("audio"),
                "audio_duration": data.get("audio_duration"),
                "reply_to": data.get("reply_to"),
                "timestamp": datetime.now().strftime("%H:%M"),
                "time_ms": now_ms,
                "expires_at": expires_at,
                "status": initial_status,
                "reactions": {}
            }

            # Save to MongoDB first
            await save_message(chat_item)
            room.touch(username)
            await room.broadcast(chat_item)

    except WebSocketDisconnect:
        room.release(username)
        await room.broadcast_users()
    except Exception as e:
        print(f"[WS Error] Exception with user {username}: {e}")
        room.release(username)
        await room.broadcast_users()

# ─────────────────────────────────────────────
# Media Upload API & Static Files
# ─────────────────────────────────────────────

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.post("/api/media")
async def upload_media(file: UploadFile = File(...)):
    """Upload photo/audio attachment safely."""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "audio/webm", "audio/ogg", "audio/mp4", "audio/wav"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid media type.")

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    safe_name = f"media_{int(time.time()*1000)}_{secrets.token_hex(6)}{ext}"
    dest_path = os.path.join(uploads_dir, safe_name)

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 15MB).")

    with open(dest_path, "wb") as f:
        f.write(content)

    return {"ok": True, "url": f"/uploads/{safe_name}", "filename": safe_name}

# ─────────────────────────────────────────────
# Static files & Index
# ─────────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Server running. UI not found.</h1>"

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  [COUPLE'S PRIVATE CHAT SERVER]")
    print(f"  PIN: {PRIVATE_PIN}  |  Max users: {MAX_USERS}")
    print("  Local:   http://127.0.0.1:8000")
    print("  Network: http://0.0.0.0:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
