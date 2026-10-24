import asyncio
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="Burp Suite Chat Lab Server - Stable Edition")

# --- Room & Connection Management ---

class Room:
    def __init__(self, room_id: str, room_name: str, pin: str, host: str = "Admin"):
        self.room_id = room_id  # Pin acts as room_id
        self.pin = pin
        self.room_name = room_name
        self.host = host
        self.connections: Dict[str, WebSocket] = {}
        self.messages: List[Dict] = []
        self.created_at = time.time()

    async def broadcast(self, message: dict):
        """Safely broadcast to all active connections, cleaning dead sockets"""
        dead_users = []
        for username, ws in list(self.connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                dead_users.append(username)

        for u in dead_users:
            if u in self.connections:
                del self.connections[u]

    async def broadcast_users(self):
        msg = {
            "type": "users_update",
            "users": list(self.connections.keys()),
            "host": self.host
        }
        await self.broadcast(msg)

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # Default public lobby room
        self.rooms["general"] = Room("general", "General Public Chat", "0000", host="System")

    def generate_pin(self) -> str:
        """Generate unique 4-digit PIN (1000 to 9999)"""
        for _ in range(10000):
            pin = f"{random.randint(1000, 9999)}"
            if pin not in self.rooms:
                return pin
        return f"{random.randint(10000, 99999)}"

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id.strip())

    def get_or_create(self, pin: str, name: str = "", host: str = "Host") -> Room:
        clean_pin = pin.strip()
        if clean_pin not in self.rooms:
            self.rooms[clean_pin] = Room(room_id=clean_pin, room_name=name or f"Room #{clean_pin}", pin=clean_pin, host=host)
        return self.rooms[clean_pin]

    def delete_room(self, room_id: str):
        if room_id in self.rooms and room_id != "general":
            del self.rooms[room_id]

manager = RoomManager()

# --- Pydantic Models ---

class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = "Private Chat"
    creator: Optional[str] = "Host"
    custom_pin: Optional[str] = None

class JoinRoomRequest(BaseModel):
    pin: str
    username: str

class ChatMessagePayload(BaseModel):
    sender: str
    content: str
    msg_id: Optional[str] = None

# --- REST Endpoints ---

@app.post("/api/rooms/create")
async def create_room(req: CreateRoomRequest):
    if req.custom_pin and req.custom_pin.strip():
        pin = req.custom_pin.strip()
    else:
        pin = manager.generate_pin()

    creator_name = req.creator.strip() if req.creator else "Host"
    name = req.room_name.strip() if req.room_name else f"Room #{pin}"
    room = Room(room_id=pin, room_name=name, pin=pin, host=creator_name)
    manager.rooms[pin] = room

    return {
        "status": "created",
        "pin": pin,
        "room_name": name,
        "host": creator_name,
        "message": f"Room created successfully! Share PIN: {pin}"
    }

@app.post("/api/rooms/join")
async def join_room(req: JoinRoomRequest):
    pin = req.pin.strip()
    # Auto-recover/find room so serverless lambdas never fail with 404
    room = manager.get_or_create(pin)

    return {
        "status": "authorized",
        "pin": room.pin,
        "room_name": room.room_name,
        "host": room.host,
        "username": req.username
    }

@app.get("/api/rooms/{pin}/messages")
async def get_room_messages(pin: str, since_id: Optional[str] = None):
    room = manager.get_or_create(pin)
    
    # If since_id provided, return only new messages for fast sync
    if since_id:
        idx = -1
        for i, m in enumerate(room.messages):
            if m.get("id") == since_id:
                idx = i
                break
        if idx != -1:
            return {"pin": room.pin, "room_name": room.room_name, "host": room.host, "messages": room.messages[idx+1:]}

    return {"pin": room.pin, "room_name": room.room_name, "host": room.host, "messages": room.messages}

@app.post("/api/rooms/{pin}/send")
async def send_room_message(pin: str, msg: ChatMessagePayload, request: Request):
    # Auto-recover/find room so serverless lambdas never fail with 404
    room = manager.get_or_create(pin)

    message_id = msg.msg_id or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
    now_ms = int(time.time() * 1000)
    chat_item = {
        "id": message_id,
        "type": "chat",
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "time_ms": now_ms,
        "client_ip": request.client.host if request.client else "unknown"
    }
    room.messages.append(chat_item)
    await room.broadcast(chat_item)
    return {"status": "success", "message": chat_item}

@app.post("/api/rooms/{pin}/close")
async def close_room_immediately(pin: str, msg: ChatMessagePayload):
    """Explicitly delete room when host clicks 'Delete Room'"""
    room = manager.get_room(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    closed_event = {
        "type": "room_closed",
        "content": f"The Host ({msg.sender}) has closed and deleted this room.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await room.broadcast(closed_event)
    for client_user, ws in list(room.connections.items()):
        try:
            await ws.close(code=1000)
        except Exception:
            pass
    manager.delete_room(pin)
    return {"status": "closed"}

@app.delete("/api/rooms/{pin}/messages")
async def clear_room_messages(pin: str):
    room = manager.get_room(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room.messages.clear()
    clear_msg = {
        "type": "system",
        "sender": "System",
        "content": "Chat history was cleared.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await room.broadcast(clear_msg)
    return {"status": "cleared"}

# Legacy endpoints
@app.get("/api/messages")
async def legacy_get_messages():
    return await get_room_messages("general")

@app.post("/api/send")
async def legacy_send_message(msg: ChatMessagePayload, request: Request):
    return await send_room_message("general", msg, request)

@app.get("/api/users")
async def legacy_get_users():
    room = manager.get_room("general")
    return {"active_users": list(room.connections.keys()) if room else []}

# --- WebSocket Room Endpoint (Robust & Reconnection-Safe) ---

@app.websocket("/ws/{pin}/{username}")
async def websocket_room_endpoint(websocket: WebSocket, pin: str, username: str):
    clean_pin = pin.strip()
    room = manager.get_room(clean_pin)

    if not room:
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": f"Room with PIN {clean_pin} not found."})
        await websocket.close(code=4004)
        return

    await websocket.accept()
    # If connection was already open for this username, replace it safely
    room.connections[username] = websocket

    is_host = (username == room.host)
    join_msg = {
        "id": f"sys_{int(time.time()*1000)}",
        "type": "system",
        "sender": "System",
        "content": f"{username} {'(Host)' if is_host else ''} connected.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    # Broadcast user status
    await room.broadcast_users()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            # Heartbeat ping/pong (prevents timeouts on proxies/routers)
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            message_id = data.get("msg_id") or f"m_{int(time.time()*1000)}_{random.randint(100, 999)}"
            chat_item = {
                "id": message_id,
                "type": "chat",
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "time_ms": int(time.time() * 1000)
            }
            room.messages.append(chat_item)
            await room.broadcast(chat_item)
    except WebSocketDisconnect:
        # Safely remove this connection
        if username in room.connections and room.connections[username] == websocket:
            del room.connections[username]

        # Stable Room Policy: Room stays ALIVE!
        # Even if someone switches tabs, minimizes their phone, or disconnects,
        # the room persists so they can smoothly reconnect without losing the chat.
        await room.broadcast_users()
    except Exception:
        if username in room.connections and room.connections[username] == websocket:
            del room.connections[username]

# --- Static UI ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Server is running. Web UI not found.</h1>"

if __name__ == "__main__":
    print("==================================================================")
    print("  Burp Suite Chat Lab Server (High-Stability Edition)")
    print("  Local access:    http://127.0.0.1:8000")
    print("  Network access:  http://0.0.0.0:8000")
    print("==================================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
