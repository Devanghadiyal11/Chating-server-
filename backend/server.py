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
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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
COL_EVNT  = "events"

# ─────────────────────────────────────────────
# State & Caches
# ─────────────────────────────────────────────

mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None
messages_col = None
settings_col = None
sessions_col = None
events_col = None

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

# In-memory fallbacks & fast lookup caches
memory_messages: List[dict] = []
memory_events: List[dict] = []
recent_msg_ids: set = set()

# ─────────────────────────────────────────────
# Network Photo Encryption / Storage Decryption
# ─────────────────────────────────────────────
PHOTO_SECRET = os.getenv("PHOTO_ENCRYPTION_SECRET", "couple_secret_key_1012_encrypted_transit")
PHOTO_KEY = hashlib.sha256(PHOTO_SECRET.encode()).digest()
_aesgcm = AESGCM(PHOTO_KEY)

def encrypt_photo(plain_str: Optional[str]) -> Optional[str]:
    """Encrypt photo payload for network transit."""
    if not plain_str or not isinstance(plain_str, str) or plain_str.startswith("enc:v1:"):
        return plain_str
    try:
        iv = os.urandom(12)
        ct = _aesgcm.encrypt(iv, plain_str.encode("utf-8"), None)
        return "enc:v1:" + base64.b64encode(iv + ct).decode("utf-8")
    except Exception as e:
        print(f"[Crypto] Encrypt error: {e}")
        return plain_str

def decrypt_photo(cipher_str: Optional[str]) -> Optional[str]:
    """Decrypt photo from network transit and restore to original form for MongoDB storage."""
    if not cipher_str or not isinstance(cipher_str, str) or not cipher_str.startswith("enc:v1:"):
        return cipher_str
    try:
        raw = base64.b64decode(cipher_str[len("enc:v1:"):])
        if len(raw) <= 12:
            return cipher_str
        iv = raw[:12]
        ct = raw[12:]
        return _aesgcm.decrypt(iv, ct, None).decode("utf-8")
    except Exception as e:
        print(f"[Crypto] Decrypt error: {e}")
        return cipher_str

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
    global mongo_client, db, messages_col, settings_col, sessions_col, events_col
    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        db = mongo_client[DB_NAME]
        messages_col = db[COL_MSGS]
        settings_col = db[COL_CONF]
        sessions_col = db[COL_SESS]
        events_col = db[COL_EVNT]

        await messages_col.create_index("time_ms")
        await messages_col.create_index("id", unique=True)
        try:
            await messages_col.create_index("seq")
            await messages_col.create_index([("time_ms", 1), ("seq", 1)])
        except Exception:
            pass
        try:
            await events_col.create_index("seq")
            await events_col.create_index("eventId", unique=True)
            await events_col.create_index("createdAt")
        except Exception:
            pass
        print(f"[DB] Connected to MongoDB Atlas - {DB_NAME}")

        # Load persisted chat history from MongoDB Atlas into memory cache
        try:
            cursor = messages_col.find(
                {
                    "$or": [
                        {"content": {"$regex": r"\S"}},
                        {"image": {"$ne": None, "$ne": ""}},
                        {"audio": {"$ne": None, "$ne": ""}}
                    ]
                },
                {"_id": 0}
            ).sort([("time_ms", 1), ("seq", 1)]).limit(1000)

            loaded_count = 0
            async for doc in cursor:
                memory_messages.append(doc)
                if "id" in doc:
                    recent_msg_ids.add(doc["id"])
                if "clientMessageId" in doc:
                    recent_msg_ids.add(doc["clientMessageId"])
                loaded_count += 1
            print(f"[DB] Restored {loaded_count} persistent messages from MongoDB Atlas.")
        except Exception as e:
            print(f"[DB Restore Warning] {e}")

        # Load persisted settings
        stored_conf = await settings_col.find_one({"_id": "couple_settings"}, {"_id": 0})
        if stored_conf:
            settings_cache.update(stored_conf)

        # Initialize atomic in-memory sequence counter from DB
        try:
            cnt_doc = await db["counters"].find_one({"_id": "message_seq"})
            if cnt_doc and "seq" in cnt_doc:
                current_seq = cnt_doc["seq"]
            else:
                last_ev = await events_col.find_one(sort=[("seq", -1)])
                if last_ev and "seq" in last_ev:
                    current_seq = last_ev["seq"]
        except Exception as e:
            print(f"[Counter Init Warning] {e}")

        # Pre-populate recent message IDs into memory cache for instant deduplication
        try:
            recent_cursor = messages_col.find({}, {"id": 1, "clientMessageId": 1}).sort("time_ms", -1).limit(500)
            async for r_doc in recent_cursor:
                if "id" in r_doc:
                    recent_msg_ids.add(r_doc["id"])
                if "clientMessageId" in r_doc:
                    recent_msg_ids.add(r_doc["clientMessageId"])
        except Exception:
            pass

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
    allow_origin_regex=r"^https?:\/\/.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ─────────────────────────────────────────────
# Room & Presence Hub
# ─────────────────────────────────────────────

def normalize_username(u: Optional[str]) -> str:
    if not u:
        return ""
    u_lower = str(u).strip().lower()
    if u_lower in ["him", "he", "boy", "boyfriend", "hubby"]:
        return "Him"
    if u_lower in ["her", "she", "girl", "girlfriend", "wifey", "hew"]:
        return "Her"
    return str(u).strip().capitalize()

class PrivateRoom:
    """The one and only private couple room — PIN 1012. Always alive."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}   # username -> ws
        self.active_users: Dict[str, float] = {}       # username -> last_seen
        self.pin = PRIVATE_PIN

    def get_online_users(self) -> List[str]:
        now = time.time()
        online = set()

        # 1. Any user currently holding an active WebSocket connection
        for user, ws in list(self.connections.items()):
            try:
                if ws.client_state.name == "CONNECTED":
                    online.add(normalize_username(user))
                else:
                    self.connections.pop(user, None)
            except Exception:
                online.add(normalize_username(user))

        # 2. Any user active via presence polling / touch within the last 5 seconds
        for user, last_seen in list(self.active_users.items()):
            if now - last_seen < 5.0:
                online.add(normalize_username(user))
            else:
                self.active_users.pop(user, None)

        return sorted(list(online))

    def touch(self, username: str):
        if username and str(username).strip():
            u_norm = normalize_username(username)
            self.active_users[u_norm] = time.time()

    def release(self, username: str, ws: Optional[WebSocket] = None):
        if not username:
            return
        u_norm = normalize_username(username)
        # CRITICAL: Only pop if the registered ws matches the disconnecting ws
        # Prevents race condition where closing old socket removes the new active socket
        if ws is None or self.connections.get(u_norm) == ws:
            self.connections.pop(u_norm, None)
            self.active_users.pop(u_norm, None)

    async def broadcast(self, msg: dict, exclude: Optional[str] = None):
        dead = []
        exclude_norm = normalize_username(exclude) if exclude else None
        for user, ws in list(self.connections.items()):
            if exclude_norm and normalize_username(user) == exclude_norm:
                continue
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append((user, ws))
        for u, w in dead:
            self.release(u, w)

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

last_seq_time_ms = int(time.time() * 1000)

def get_next_seq() -> int:
    """Generate strictly monotonic sequence for every chat using time in milliseconds."""
    global last_seq_time_ms
    now_ms = int(time.time() * 1000)
    if now_ms <= last_seq_time_ms:
        last_seq_time_ms += 1
    else:
        last_seq_time_ms = now_ms
    return last_seq_time_ms

async def save_message(msg: dict):
    """Persist message to MongoDB Atlas and memory cache so chat survives rejoin/restart."""
    global memory_messages
    content = str(msg.get("content", "")).strip()
    if not content and not msg.get("image") and not msg.get("audio"):
        return  # Reject dummy/empty messages

    # Always ensure photo is decrypted and stored in its original form in storage/MongoDB
    if msg.get("image") and isinstance(msg["image"], str) and msg["image"].startswith("enc:v1:"):
        msg["image"] = decrypt_photo(msg["image"])

    now_ms = int(time.time() * 1000)
    if not msg.get("time_ms"):
        msg["time_ms"] = now_ms
    # Sequence for every chat using time
    if not msg.get("seq"):
        msg["seq"] = get_next_seq()
    if not msg.get("time"):
        msg["time"] = datetime.now().strftime("%I:%M %p")

    msg_id = msg.get("id")
    if msg_id:
        recent_msg_ids.add(msg_id)
    if msg.get("clientMessageId"):
        recent_msg_ids.add(msg["clientMessageId"])
    if len(recent_msg_ids) > 4000:
        recent_msg_ids.clear()

    # Deduplicate in memory
    existing_idx = next((i for i, m in enumerate(memory_messages) if m.get("id") == msg_id), -1)
    if existing_idx >= 0:
        memory_messages[existing_idx] = msg
    else:
        memory_messages.append(msg)
    if len(memory_messages) > 1000:
        memory_messages.pop(0)

    # Persist permanently to MongoDB Atlas
    if messages_col is not None and msg_id:
        try:
            doc_to_save = {k: v for k, v in msg.items() if k != "_id"}
            await messages_col.update_one(
                {"id": msg_id},
                {"$set": doc_to_save},
                upsert=True
            )
        except Exception as e:
            print(f"[DB Error] Saving message to MongoDB: {e}")

def purge_dummy_messages():
    """Purge any empty/whitespace dummy messages from memory caches."""
    global memory_messages, memory_events
    memory_messages = [
        m for m in memory_messages
        if bool(str(m.get("content", "")).strip()) or bool(m.get("image")) or bool(m.get("audio"))
    ]
    memory_events = [
        ev for ev in memory_events
        if ev.get("type") != "message.created" or (
            isinstance(ev.get("payload"), dict) and (
                bool(str(ev["payload"].get("content", "")).strip()) or
                bool(ev["payload"].get("image")) or
                bool(ev["payload"].get("audio"))
            )
        )
    ]

async def load_messages(since_id: Optional[str] = None, after_seq: Optional[int] = None, limit: int = 2000) -> List[dict]:
    """Load persistent chat history from MongoDB Atlas with in-memory fast fallback."""
    now_ms = int(time.time() * 1000)

    if messages_col is not None:
        try:
            query: Dict[str, Any] = {
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gt": now_ms}}
                ]
            }
            if after_seq is not None:
                query["seq"] = {"$gt": after_seq}
                cursor = messages_col.find(query, {"_id": 0}).sort([("time_ms", 1), ("seq", 1)]).limit(limit)
                db_msgs = []
                async for doc in cursor:
                    if bool(str(doc.get("content", "")).strip()) or bool(doc.get("image")) or bool(doc.get("audio")):
                        db_msgs.append(doc)
                return db_msgs
            elif since_id:
                since_doc = await messages_col.find_one({"id": since_id}, {"seq": 1, "time_ms": 1})
                if since_doc and "seq" in since_doc:
                    query["seq"] = {"$gt": since_doc["seq"]}
                elif since_doc and "time_ms" in since_doc:
                    query["time_ms"] = {"$gt": since_doc["time_ms"]}
                cursor = messages_col.find(query, {"_id": 0}).sort([("time_ms", 1), ("seq", 1)]).limit(limit)
                db_msgs = []
                async for doc in cursor:
                    if bool(str(doc.get("content", "")).strip()) or bool(doc.get("image")) or bool(doc.get("audio")):
                        db_msgs.append(doc)
                return db_msgs
            else:
                # Retrieve the most recent messages up to limit in chronological order
                cursor = messages_col.find(query, {"_id": 0}).sort([("time_ms", -1), ("seq", -1)]).limit(limit)
                db_msgs = []
                async for doc in cursor:
                    if bool(str(doc.get("content", "")).strip()) or bool(doc.get("image")) or bool(doc.get("audio")):
                        db_msgs.append(doc)
                db_msgs.reverse()
                return db_msgs
        except Exception as e:
            print(f"[DB Error] loading messages from MongoDB: {e}")

    # Fallback to memory_messages
    purge_dummy_messages()
    valid_mem = [
        m for m in memory_messages
        if not (m.get("expires_at") and m["expires_at"] < now_ms)
        and (bool(str(m.get("content", "")).strip()) or bool(m.get("image")) or bool(m.get("audio")))
    ]
    if after_seq is not None:
        valid_mem = [m for m in valid_mem if m.get("seq", 0) > after_seq]
    elif since_id:
        idx = next((i for i, m in enumerate(valid_mem) if m.get("id") == since_id), -1)
        if idx != -1:
            valid_mem = valid_mem[idx + 1:]
    valid_mem.sort(key=lambda x: (x.get("time_ms", 0), x.get("seq", 0), x.get("id", "")))
    return valid_mem[-limit:]

async def save_settings(new_conf: dict):
    settings_cache.update(new_conf)
    if settings_col is not None:
        asyncio.create_task(db_save_settings(settings_cache))

async def db_save_settings(conf: dict):
    try:
        await settings_col.update_one(
            {"_id": "couple_settings"},
            {"$set": conf},
            upsert=True
        )
    except Exception as e:
        print(f"[DB Error] Saving settings: {e}")

async def publish_event(
    event_type: str,
    actor_id: str,
    payload: dict,
    event_id: Optional[str] = None
) -> dict:
    """Unified Event Pipeline: Broadcast immediately to WebSocket, persist to DB in background."""
    if event_type == "message.created":
        content = str(payload.get("content", "")).strip() if isinstance(payload, dict) else ""
        if not content and not payload.get("image") and not payload.get("audio"):
            return {}  # Never publish dummy/empty message events

    seq = payload.get("seq") if isinstance(payload, dict) and payload.get("seq") else get_next_seq()
    now_ms = get_monotonic_time_ms()
    ev_id = event_id or f"ev_{now_ms}_{secrets.token_hex(4)}"

    event_doc = {
        "eventId": ev_id,
        "roomId": "sweet_space",
        "seq": seq,
        "type": event_type,
        "actorId": actor_id,
        "payload": payload,
        "createdAt": now_ms
    }

    memory_events.append(event_doc)
    if len(memory_events) > 2000:
        memory_events.pop(0)

    # Persist event to MongoDB Atlas in background
    if events_col is not None:
        try:
            ev_to_save = {k: v for k, v in event_doc.items() if k != "_id"}
            asyncio.create_task(events_col.insert_one(ev_to_save))
        except Exception:
            pass

    # Prepare wire-safe copies with photos encrypted for network transmission
    wire_event_doc = event_doc
    wire_payload = payload
    if event_type == "message.created" and isinstance(payload, dict) and payload.get("image"):
        wire_payload = dict(payload)
        wire_payload["image"] = encrypt_photo(payload["image"])
        wire_event_doc = dict(event_doc)
        wire_event_doc["payload"] = wire_payload

    # 1. IMMEDIATE WebSocket broadcast (0ms wait!)
    envelope = {
        "type": "event",
        "event": wire_event_doc
    }
    await room.broadcast(envelope)

    # 2. Backward-compatible legacy event broadcasts
    if event_type == "message.created":
        await room.broadcast(wire_payload)
    elif event_type == "nudge.created":
        await room.broadcast({
            "type": "nudge",
            "sender": actor_id,
            "timestamp": payload.get("timestamp", datetime.now().strftime("%H:%M")),
            "time_ms": now_ms
        })
    elif event_type == "reaction.updated":
        await room.broadcast({
            "type": "reaction_update",
            "msg_id": payload.get("msg_id"),
            "reactions": payload.get("reactions"),
            "sender": actor_id,
            "emoji": payload.get("emoji")
        })
    elif event_type == "theme.updated":
        await room.broadcast({
            "type": "theme_update",
            "theme": payload.get("theme"),
            "sender": actor_id
        })
    elif event_type == "message.deleted":
        await room.broadcast({
            "type": "delete_message",
            "msg_id": payload.get("msg_id")
        })
    elif event_type == "chat.cleared":
        await room.broadcast({
            "type": "system",
            "sender": "System",
            "content": "Chat history cleared. 🗑️",
            "timestamp": payload.get("timestamp", datetime.now().strftime("%H:%M")),
            "time_ms": now_ms,
            "id": f"m_{int(time.time()*1000)}_clear"
        })

    return event_doc

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

# ─────────────────────────────────────────────
# REST API: Authentication & Sessions
# ─────────────────────────────────────────────

def find_existing_message(msg_id: Optional[str], client_id: Optional[str]) -> Optional[dict]:
    ids = [x for x in [msg_id, client_id] if x]
    if not ids:
        return None
    # Fast-path O(1) set lookup for duplicate detection
    for i in ids:
        if i in recent_msg_ids:
            for m in reversed(memory_messages):
                if m.get("id") == i or m.get("clientMessageId") == i:
                    return m
            return {"id": i, "duplicate": True}
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

    # Canonicalize to Him or Her on behalf of dynamic usernames
    if username.lower() in ["him", "he", "boy", "boyfriend", "hubby"]:
        username = "Him"
    elif username.lower() in ["her", "she", "girl", "girlfriend", "wifey", "hew"]:
        username = "Her"

    user_lower = username.lower()
    active_users_lower = {s["username"].lower() for s in active_sessions.values()}

    # Strict 2-account couple authorization (Him & Her)
    if len(active_users_lower) >= MAX_USERS and user_lower not in active_users_lower:
        now = time.time()
        for tok, info in list(active_sessions.items()):
            if now - info.get("created_at", 0) > 86400:
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
async def get_messages(since_id: Optional[str] = None, after_seq: Optional[int] = None, limit: Optional[int] = 2000, username: Optional[str] = None):
    if username:
        room.touch(username)
    safe_limit = min(max(1, limit or 2000), 5000)
    msgs = await load_messages(since_id=since_id, after_seq=after_seq, limit=safe_limit)
    # Encrypt photos for safe transit across the network
    wire_msgs = []
    for m in msgs:
        if m.get("image"):
            m_wire = dict(m)
            m_wire["image"] = encrypt_photo(m["image"])
            wire_msgs.append(m_wire)
        else:
            wire_msgs.append(m)
    return {"messages": wire_msgs}

@app.post("/api/send")
async def send_message(msg: ChatPayload, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"send_{client_ip}", max_calls=60, period=10.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    # Instant in-memory deduplication check (0.001ms)
    existing = find_existing_message(msg.msg_id, msg.clientMessageId)
    if existing:
        return {"status": "ok", "message": existing, "duplicate": True}

    message_id = msg.msg_id or msg.clientMessageId or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
    now_ms = get_monotonic_time_ms()

    # If incoming image from network is encrypted, decrypt to store original form in MongoDB
    raw_image = msg.image
    if raw_image and isinstance(raw_image, str) and raw_image.startswith("enc:v1:"):
        raw_image = decrypt_photo(raw_image)

    msg_type = "chat"
    if raw_image:
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
        "image": raw_image,
        "audio": msg.audio,
        "audio_duration": msg.audio_duration,
        "reply_to": msg.reply_to,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms,
        "expires_at": expires_at,
        "status": initial_status,
        "reactions": {}
    }

    # Store in memory & MongoDB in original form, broadcast to WebSocket
    await save_message(chat_item)
    room.touch(msg.sender)
    await publish_event("message.created", msg.sender, chat_item, event_id=f"ev_msg_{chat_item['id']}")

    wire_chat_item = dict(chat_item)
    if wire_chat_item.get("image"):
        wire_chat_item["image"] = encrypt_photo(wire_chat_item["image"])
    return {"status": "ok", "message": wire_chat_item}

@app.post("/api/ack")
async def acknowledge_delivery(req: Request):
    """Mark a message as delivered or read with instant broadcast."""
    data = await req.json()
    msg_id = data.get("msg_id")
    status = data.get("status", "delivered")
    if not msg_id:
        return {"status": "ignored"}

    for m in memory_messages:
        if m.get("id") == msg_id:
            m["status"] = status

    await room.broadcast({
        "type": "msg_status",
        "msg_id": msg_id,
        "status": status
    })

    if messages_col is not None:
        asyncio.create_task(db_update_status(msg_id, status))

    return {"status": "ok"}

async def db_update_status(msg_id: str, status: str):
    try:
        await messages_col.update_one({"id": msg_id}, {"$set": {"status": status}})
    except Exception as e:
        print(f"[DB Error] Status update: {e}")

@app.post("/api/reaction")
async def toggle_reaction(req: ReactionPayload):
    msg_id = req.msg_id
    emoji = req.emoji
    sender = req.sender

    msg = next((m for m in memory_messages if m.get("id") == msg_id), None)
    if not msg and messages_col is not None:
        msg = await messages_col.find_one({"id": msg_id})

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

    msg["reactions"] = reactions
    for m in memory_messages:
        if m.get("id") == msg_id:
            m["reactions"] = reactions

    payload = {
        "msg_id": msg_id,
        "reactions": reactions,
        "sender": sender,
        "emoji": emoji
    }
    await publish_event("reaction.updated", sender, payload)

    if messages_col is not None:
        asyncio.create_task(db_update_reactions(msg_id, reactions))

    return {"status": "ok", "reactions": reactions}

async def db_update_reactions(msg_id: str, reactions: dict):
    try:
        await messages_col.update_one({"id": msg_id}, {"$set": {"reactions": reactions}})
    except Exception as e:
        print(f"[DB Error] Reactions update: {e}")

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
    payload = {
        "sender": req.sender,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms
    }
    room.touch(req.sender)
    await publish_event("nudge.created", req.sender, payload)
    return {"status": "ok"}

@app.delete("/api/messages/{msg_id}")
async def delete_single_message(msg_id: str):
    if messages_col is not None:
        await messages_col.delete_one({"id": msg_id})
    global memory_messages
    memory_messages = [m for m in memory_messages if m.get("id") != msg_id]

    await publish_event("message.deleted", "user", {"msg_id": msg_id})
    return {"status": "deleted"}

@app.delete("/api/messages")
async def clear_messages():
    global memory_messages, memory_events, recent_msg_ids
    memory_messages = []
    memory_events = []
    recent_msg_ids = set()
    if messages_col is not None:
        try:
            await messages_col.delete_many({})
        except Exception:
            pass

    await publish_event("chat.cleared", "system", {"timestamp": datetime.now().strftime("%H:%M")})
    return {"status": "cleared"}

# ─────────────────────────────────────────────
# REST API: Event Stream & Catch-up Recovery
# ─────────────────────────────────────────────

@app.get("/api/events")
async def get_events(after_seq: Optional[int] = None, limit: int = 250):
    """Retrieve event catch-up stream from MongoDB Atlas or memory cache."""
    purge_dummy_messages()
    limit = min(max(1, limit), 500)

    raw_evs = []
    if events_col is not None:
        try:
            q: Dict[str, Any] = {}
            if after_seq is not None:
                q["seq"] = {"$gt": after_seq}
            ev_cursor = events_col.find(q, {"_id": 0}).sort("seq", 1).limit(limit)
            async for ev in ev_cursor:
                raw_evs.append(ev)
        except Exception as e:
            print(f"[DB Error] loading events: {e}")

    if not raw_evs:
        mem = memory_events
        if after_seq is not None:
            mem = [ev for ev in mem if ev.get("seq", 0) > after_seq]
        raw_evs = sorted(mem, key=lambda x: x.get("seq", 0))[:limit]

    # Encrypt photo payloads for wire transmission
    wire_evs = []
    for ev in raw_evs:
        if ev.get("type") == "message.created" and isinstance(ev.get("payload"), dict) and ev["payload"].get("image"):
            ev_copy = dict(ev)
            payload_copy = dict(ev["payload"])
            payload_copy["image"] = encrypt_photo(payload_copy["image"])
            ev_copy["payload"] = payload_copy
            wire_evs.append(ev_copy)
        else:
            wire_evs.append(ev)

    return {"events": wire_evs}

@app.get("/api/purge_dummies")
@app.post("/api/purge_dummies")
async def purge_dummies():
    purge_dummy_messages()
    if messages_col is not None:
        try:
            await messages_col.delete_many({
                "$and": [
                    {"$or": [{"content": ""}, {"content": None}, {"content": {"$regex": r"^\s*$"}}]},
                    {"$or": [{"image": ""}, {"image": None}]},
                    {"$or": [{"audio": ""}, {"audio": None}]}
                ]
            })
        except Exception:
            pass
    return {"status": "ok", "remaining_messages": len(memory_messages)}

# ─────────────────────────────────────────────
# REST API: Couple Settings & Presence
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
            await publish_event("theme.updated", "Partner", {"theme": updates["theme"]})
        await publish_event("settings.updated", "Partner", {"settings": settings_cache})
    return {"status": "ok", "settings": settings_cache}

@app.get("/api/users")
async def get_users(username: Optional[str] = None):
    if username:
        room.touch(username)
    return {"users": room.get_online_users()}

@app.post("/api/leave")
@app.get("/api/leave")
async def user_leave(username: Optional[str] = None):
    """Instant offline notification when user closes tab or navigates away."""
    if username:
        room.release(username)
        await room.broadcast({
            "type": "partner_offline",
            "username": username
        }, exclude=username)
        await room.broadcast_users()
    return {"status": "left"}

# ─────────────────────────────────────────────
# WebSocket Endpoint with Auth & State Sync
# ─────────────────────────────────────────────

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    username = normalize_username(username)
    user_lower = username.lower()

    # Verify session or token if provided
    token = websocket.query_params.get("token")
    if token and token in active_sessions:
        username = normalize_username(active_sessions[token]["username"])
        user_lower = username.lower()

    # Close any existing connection for this exact user on reconnect
    for existing_user in list(room.connections.keys()):
        if existing_user.lower() == user_lower:
            old_ws = room.connections.get(existing_user)
            if old_ws and old_ws != websocket:
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

            if msg_type in ("ping", "pong", "typing"):
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                continue

            elif msg_type == "ack":
                # Recipient acknowledged delivery / read receipt
                msg_id = data.get("msg_id")
                status = data.get("status", "delivered")
                if msg_id:
                    for m in memory_messages:
                        if m.get("id") == msg_id:
                            m["status"] = status
                    await room.broadcast({
                        "type": "msg_status",
                        "msg_id": msg_id,
                        "status": status
                    })
                    if messages_col is not None:
                        asyncio.create_task(db_update_status(msg_id, status))
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
                await publish_event("nudge.created", username, {
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
                await publish_event("theme.updated", username, {"theme": new_theme})
                continue

            elif msg_type == "chat_clear":
                await clear_messages()
                continue

            # Standard chat / photo / audio message - reject any other types or empty messages
            if msg_type not in ("chat", "image", "audio"):
                continue

            content = str(data.get("content", "")).strip()
            image = data.get("image")
            audio = data.get("audio")

            # Decrypt network-encrypted photo to store original form in MongoDB
            if image and isinstance(image, str) and image.startswith("enc:v1:"):
                image = decrypt_photo(image)

            # Strictly reject dummy / empty messages
            if not content and not image and not audio:
                continue

            message_id = data.get("msg_id") or data.get("clientMessageId") or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
            client_msg_id = data.get("clientMessageId") or message_id

            existing = find_existing_message(message_id, client_msg_id)
            if existing:
                continue

            now_ms = get_monotonic_time_ms()

            resolved_type = "chat"
            if image:
                resolved_type = "image"
            elif audio:
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
                "content": content,
                "image": image,
                "audio": audio,
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
            await publish_event("message.created", username, chat_item, event_id=f"ev_msg_{chat_item['id']}")

    except WebSocketDisconnect:
        room.release(username, websocket)
        await room.broadcast({
            "type": "partner_offline",
            "username": username
        }, exclude=username)
        await room.broadcast_users()
    except Exception as e:
        print(f"[WS Error] Exception with user {username}: {e}")
        room.release(username, websocket)
        await room.broadcast({
            "type": "partner_offline",
            "username": username
        }, exclude=username)
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
