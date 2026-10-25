"""
Private Chat Server - 2-Person Only
PIN: 1012 (hardcoded, always alive)
Storage: MongoDB (persistent - chats survive server restarts)
"""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

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
MAX_USERS   = 2  # Only 2 people allowed

MONGO_URI = "mongodb+srv://devanghadiyal:dev%40ng%7B8954%7D@cluster0.owtzs.mongodb.net/Chatserver"
DB_NAME   = "Chatserver"
COL_NAME  = "messages"

# ─────────────────────────────────────────────
# MongoDB connection (lifespan)
# ─────────────────────────────────────────────

mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None
messages_col = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, messages_col
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    messages_col = db[COL_NAME]
    await messages_col.create_index("time_ms")
    print(f"[DB] Connected to MongoDB - {DB_NAME}.{COL_NAME}")
    yield
    if mongo_client:
        mongo_client.close()

app = FastAPI(title="Private Chat - 1012", lifespan=lifespan)

# ─────────────────────────────────────────────
# In-memory room state (connections only)
# ─────────────────────────────────────────────

class PrivateRoom:
    """The one and only private room — PIN 1012. Always alive."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}   # username -> ws
        self.active_users: Dict[str, float] = {}       # username -> last_seen
        self.pin = PRIVATE_PIN

    def get_online_users(self) -> List[str]:
        now = time.time()
        online = set(self.connections.keys())
        for u, last in list(self.active_users.items()):
            if now - last < 30:
                online.add(u)
        return sorted(list(online))

    def touch(self, username: str):
        if username and username.strip():
            self.active_users[username.strip()] = time.time()

    async def broadcast(self, msg: dict):
        dead = []
        for user, ws in list(self.connections.items()):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(user)
        for u in dead:
            self.connections.pop(u, None)

    async def broadcast_users(self):
        await self.broadcast({
            "type": "users_update",
            "users": self.get_online_users()
        })


room = PrivateRoom()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def new_msg_id() -> str:
    return f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"

async def save_message(msg: dict):
    """Persist message to MongoDB (strip WebSocket-only fields if any)."""
    if messages_col is None:
        return
    doc = {k: v for k, v in msg.items()}
    await messages_col.insert_one(doc)

async def load_messages(since_id: Optional[str] = None) -> List[dict]:
    """Load all messages (or messages after since_id) from MongoDB."""
    if messages_col is None:
        return []

    query = {}
    if since_id:
        # Find the time_ms of the since_id message, then return everything after
        anchor = await messages_col.find_one({"id": since_id}, {"time_ms": 1})
        if anchor:
            query = {"time_ms": {"$gt": anchor["time_ms"]}}

    cursor = messages_col.find(query, {"_id": 0}).sort("time_ms", 1)
    return await cursor.to_list(length=5000)

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
    msg_id: Optional[str] = None

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

    online = room.get_online_users()
    # Allow re-join of existing user; block a 3rd new user
    if len(online) >= MAX_USERS and username not in online:
        raise HTTPException(
            status_code=403,
            detail="This private chat is full (2 people max). Come back later."
        )

    room.touch(username)
    return {
        "status": "authorized",
        "pin": PRIVATE_PIN,
        "username": username,
        "room_name": "💑 Private Chat"
    }


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
    chat_item = {
        "id": message_id,
        "type": "image" if msg.image else "chat",
        "sender": msg.sender,
        "content": msg.content or "",
        "image": msg.image,
        "timestamp": datetime.now().strftime("%H:%M"),
        "time_ms": now_ms,
    }
    await save_message(chat_item)
    room.touch(msg.sender)
    await room.broadcast(chat_item)
    return {"status": "ok", "message": chat_item}


@app.delete("/api/messages")
async def clear_messages():
    if messages_col is not None:
        await messages_col.delete_many({})
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
# WebSocket
# ─────────────────────────────────────────────

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    username = username.strip()

    online = room.get_online_users()
    if len(online) >= MAX_USERS and username not in online:
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "content": "This private chat is full. Only 2 people allowed."
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

            message_id = data.get("msg_id") or new_msg_id()
            now_ms = int(time.time() * 1000)
            chat_item = {
                "id": message_id,
                "type": "image" if data.get("image") else "chat",
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "image": data.get("image"),
                "timestamp": datetime.now().strftime("%H:%M"),
                "time_ms": now_ms
            }
            await save_message(chat_item)
            room.touch(username)
            await room.broadcast(chat_item)

    except WebSocketDisconnect:
        room.connections.pop(username, None)
        await room.broadcast_users()
    except Exception:
        room.connections.pop(username, None)

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
    print("  [PRIVATE CHAT SERVER]")
    print(f"  PIN: {PRIVATE_PIN}  |  Max users: {MAX_USERS}")
    print("  Local:   http://127.0.0.1:8000")
    print("  Network: http://0.0.0.0:8000")
    print("=" * 60)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
