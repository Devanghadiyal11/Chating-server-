"""
Private Couple Chat Server - 2-Person Only
PIN: 1012 (hardcoded, always alive)
Storage: MongoDB (persistent - chats survive server restarts)
Features: Text, Photos (view-only shield), Voice Notes, Live Typing,
          Reactions, Love Nudge, Disappearing Messages, Together Counter,
          and Stealth Mode support.
"""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

import motor.motor_asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
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

# ─────────────────────────────────────────────
# MongoDB connection & Background Tasks
# ─────────────────────────────────────────────

mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None
messages_col = None
settings_col = None

# In-memory settings cache for instant access
settings_cache: Dict[str, Any] = {
    "anniversary_date": "2024-02-14",
    "disappearing_mode": 0,  # 0 = disabled, seconds otherwise (e.g. 3600 for 1h, 86400 for 24h)
    "couple_name": "Our Sweet Space 💕",
    "theme": "rose"
}

# In-memory message store fallback if DB is temporarily unreachable
memory_messages: List[dict] = []

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
            # Also prune memory fallback
            global memory_messages
            memory_messages = [
                m for m in memory_messages
                if not (m.get("expires_at") and m["expires_at"] < now_ms)
            ]
        except Exception as e:
            print(f"[Cleanup] Error pruning expired messages: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, messages_col, settings_col, settings_cache
    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        db = mongo_client[DB_NAME]
        messages_col = db[COL_MSGS]
        settings_col = db[COL_CONF]
        await messages_col.create_index("time_ms")
        await messages_col.create_index("id", unique=True)
        print(f"[DB] Connected to MongoDB - {DB_NAME}.{COL_MSGS}")

        # Load persisted settings if any
        stored_conf = await settings_col.find_one({"_id": "couple_settings"}, {"_id": 0})
        if stored_conf:
            settings_cache.update(stored_conf)
    except Exception as e:
        print(f"[DB Warning] Could not connect to MongoDB initially: {e}. Running with memory fallback.")

    cleanup_task = asyncio.create_task(cleanup_expired_messages())
    yield
    cleanup_task.cancel()
    if mongo_client:
        mongo_client.close()

app = FastAPI(title="Couple's Private Chat - 1012", lifespan=lifespan)

# ─────────────────────────────────────────────
# In-memory room state (connections & presence)
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
# Helpers & Storage Handlers
# ─────────────────────────────────────────────

def new_msg_id() -> str:
    return f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"

async def save_message(msg: dict):
    """Persist message to MongoDB with memory fallback."""
    global memory_messages
    memory_messages.append(msg)
    if len(memory_messages) > 1000:
        memory_messages.pop(0)

    if messages_col is not None:
        try:
            doc = {k: v for k, v in msg.items()}
            await messages_col.update_one({"id": msg["id"]}, {"$set": doc}, upsert=True)
        except Exception as e:
            print(f"[DB Error] Error saving message {msg.get('id')}: {e}")

async def load_messages(since_id: Optional[str] = None) -> List[dict]:
    """Load messages (or messages after since_id) excluding expired ones."""
    now_ms = int(time.time() * 1000)
    query: Dict[str, Any] = {
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gt": now_ms}}
        ]
    }

    if messages_col is not None:
        try:
            if since_id:
                anchor = await messages_col.find_one({"id": since_id}, {"time_ms": 1})
                if anchor:
                    query["time_ms"] = {"$gt": anchor["time_ms"]}

            cursor = messages_col.find(query, {"_id": 0}).sort("time_ms", 1)
            return await cursor.to_list(length=3000)
        except Exception as e:
            print(f"[DB Error] Falling back to memory for load_messages: {e}")

    # Fallback to in-memory messages
    valid_mem = [
        m for m in memory_messages
        if not (m.get("expires_at") and m["expires_at"] < now_ms)
    ]
    if since_id:
        idx = next((i for i, m in enumerate(valid_mem) if m.get("id") == since_id), -1)
        if idx != -1:
            return valid_mem[idx + 1:]
    return valid_mem

async def save_settings(new_conf: dict):
    """Save couple settings."""
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
# Pydantic models
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
# REST Endpoints
# ─────────────────────────────────────────────

@app.post("/api/join")
async def join_room(req: JoinRequest):
    pin = req.pin.strip()
    if pin != PRIVATE_PIN:
        raise HTTPException(status_code=401, detail="Invalid PIN. Access denied.")

    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")

    current_users_lower = [u.lower() for u in room.connections.keys()]
    if len(room.connections) >= MAX_USERS and username.lower() not in current_users_lower:
        raise HTTPException(
            status_code=403,
            detail="This private room is full (2 people max). Come back later."
        )

    room.touch(username)
    return {
        "status": "authorized",
        "pin": PRIVATE_PIN,
        "username": username,
        "room_name": settings_cache.get("couple_name", "Our Sweet Space 💕"),
        "settings": settings_cache
    }

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

@app.get("/api/messages")
async def get_messages(since_id: Optional[str] = None, username: Optional[str] = None):
    if username:
        room.touch(username)
    msgs = await load_messages(since_id)
    return {"messages": msgs}

@app.post("/api/send")
async def send_message(msg: ChatPayload, request: Request):
    message_id = msg.msg_id or new_msg_id()
    now_ms = int(time.time() * 1000)

    # Determine message type
    msg_type = "chat"
    if msg.image:
        msg_type = "image"
    elif msg.audio:
        msg_type = "audio"

    # Calculate expiration if disappearing mode is active
    ttl = settings_cache.get("disappearing_mode", 0)
    expires_at = (now_ms + ttl * 1000) if ttl > 0 else None

    chat_item = {
        "id": message_id,
        "type": msg_type,
        "sender": msg.sender,
        "content": msg.content or "",
        "image": msg.image,
        "audio": msg.audio,
        "audio_duration": msg.audio_duration,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms,
        "expires_at": expires_at,
        "reactions": {}
    }
    await save_message(chat_item)
    room.touch(msg.sender)
    await room.broadcast(chat_item)
    return {"status": "ok", "message": chat_item}

@app.post("/api/reaction")
async def toggle_reaction(req: ReactionPayload):
    now_ms = int(time.time() * 1000)
    msg_id = req.msg_id
    emoji = req.emoji
    sender = req.sender

    # Fetch existing message
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

    # Update in DB & memory
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

# Cooldown tracking for Love Nudge (prevents spam and server/device load)
NUDGE_COOLDOWN_SEC = 4.0
last_nudge_times: Dict[str, float] = {}

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

    now_ms = int(now * 1000)
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
        "time_ms": int(time.time() * 1000),
        "id": new_msg_id()
    }
    await room.broadcast(clear_event)
    return {"status": "cleared"}

# ─────────────────────────────────────────────
# WebSocket Endpoint
# ─────────────────────────────────────────────

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    username = username.strip()
    user_lower = username.lower()

    # Close any existing stale connection for this exact user upon reconnect
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

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            elif msg_type == "typing":
                # Forward live typing state to other participant
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
                    # Reuse toggle logic
                    req = ReactionPayload(msg_id=msg_id, emoji=emoji, sender=username)
                    await toggle_reaction(req)
                continue

            elif msg_type == "nudge":
                sender_key = username.strip().lower()
                now = time.time()
                if now - last_nudge_times.get(sender_key, 0) < NUDGE_COOLDOWN_SEC:
                    continue  # Ignore spam during cooldown
                last_nudge_times[sender_key] = now
                now_ms = int(now * 1000)
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

            # Regular chat / photo / audio message
            message_id = data.get("msg_id") or new_msg_id()
            now_ms = int(time.time() * 1000)

            resolved_type = "chat"
            if data.get("image"):
                resolved_type = "image"
            elif data.get("audio"):
                resolved_type = "audio"

            ttl = settings_cache.get("disappearing_mode", 0)
            expires_at = (now_ms + ttl * 1000) if ttl > 0 else None

            chat_item = {
                "id": message_id,
                "type": resolved_type,
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "image": data.get("image"),
                "audio": data.get("audio"),
                "audio_duration": data.get("audio_duration"),
                "timestamp": datetime.now().strftime("%H:%M"),
                "time_ms": now_ms,
                "expires_at": expires_at,
                "reactions": {}
            }
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
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
