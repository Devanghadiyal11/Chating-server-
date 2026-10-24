import asyncio
import random
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="Burp Suite Chat Lab Server")

# --- Room & Connection Management ---

class Room:
    def __init__(self, room_id: str, room_name: str, pin: str):
        self.room_id = room_id  # Pin acts as room_id
        self.pin = pin
        self.room_name = room_name
        self.connections: Dict[str, WebSocket] = {}
        self.messages: List[Dict] = []

    async def broadcast(self, message: dict):
        for username, ws in list(self.connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_users(self):
        msg = {
            "type": "users_update",
            "users": list(self.connections.keys())
        }
        await self.broadcast(msg)

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # Default public lobby room
        self.rooms["general"] = Room("general", "General Public Chat", "0000")

    def generate_pin(self) -> str:
        """Generate unique 4-digit PIN (1000 to 9999)"""
        for _ in range(10000):
            pin = f"{random.randint(1000, 9999)}"
            if pin not in self.rooms:
                return pin
        return f"{random.randint(10000, 99999)}"

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id.strip())

manager = RoomManager()

# --- Pydantic Request Models ---

class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = "Private Chat"
    creator: Optional[str] = "User"
    custom_pin: Optional[str] = None  # Optional custom 4-digit pin

class JoinRoomRequest(BaseModel):
    pin: str
    username: str

class ChatMessagePayload(BaseModel):
    sender: str
    content: str

# --- REST Endpoints (Great for Burp Suite Interception, Intruder & Repeater) ---

@app.post("/api/rooms/create")
async def create_room(req: CreateRoomRequest):
    """
    Creates a new private room and generates a 4-digit PIN.
    Burp testing: Analyze entropy of generated PINs or specify arbitrary custom PINs.
    """
    if req.custom_pin and req.custom_pin.strip():
        pin = req.custom_pin.strip()
    else:
        pin = manager.generate_pin()

    if pin in manager.rooms:
        return {"status": "exists", "pin": pin, "room_name": manager.rooms[pin].room_name}

    name = req.room_name.strip() if req.room_name else f"Room #{pin}"
    room = Room(room_id=pin, room_name=name, pin=pin)
    manager.rooms[pin] = room

    return {
        "status": "created",
        "pin": pin,
        "room_name": name,
        "message": f"Room created successfully! Share 4-digit PIN: {pin}"
    }

@app.post("/api/rooms/join")
async def join_room(req: JoinRoomRequest):
    """
    Verifies if a 4-digit PIN exists.
    Burp Intruder Exercise:
    Since PIN is 4 digits (0000-9999), you can use Burp Intruder to brute force active room PINs!
    """
    pin = req.pin.strip()
    room = manager.get_room(pin)
    if not room:
        raise HTTPException(
            status_code=404, 
            detail=f"Room with PIN '{pin}' not found! Check the PIN and try again."
        )

    return {
        "status": "authorized",
        "pin": room.pin,
        "room_name": room.room_name,
        "username": req.username
    }

@app.get("/api/rooms/{pin}/messages")
async def get_room_messages(pin: str):
    """
    Retrieve message history for room with this 4-digit PIN.
    Burp Exercise: Test IDOR by changing the PIN in the URL.
    """
    room = manager.get_room(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"pin": room.pin, "room_name": room.room_name, "messages": room.messages}

@app.post("/api/rooms/{pin}/send")
async def send_room_message(pin: str, msg: ChatMessagePayload, request: Request):
    """
    Send a message via HTTP POST into a room using its 4-digit PIN.
    Burp Exercise: Intercept and alter sender name or message contents.
    """
    room = manager.get_room(pin)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    chat_item = {
        "type": "chat",
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "client_ip": request.client.host if request.client else "unknown"
    }
    room.messages.append(chat_item)
    await room.broadcast(chat_item)
    return {"status": "success", "message": chat_item}

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

# Legacy endpoints for backward compatibility
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

# --- WebSocket Room Endpoint ---

@app.websocket("/ws/{pin}/{username}")
async def websocket_room_endpoint(websocket: WebSocket, pin: str, username: str):
    clean_pin = pin.strip()
    room = manager.get_room(clean_pin)

    if not room:
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": f"Room with PIN {clean_pin} does not exist."})
        await websocket.close(code=4004)
        return

    await websocket.accept()
    room.connections[username] = websocket

    join_msg = {
        "type": "system",
        "sender": "System",
        "content": f"{username} joined the chat.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    room.messages.append(join_msg)
    await room.broadcast(join_msg)
    await room.broadcast_users()

    try:
        while True:
            data = await websocket.receive_json()
            # Handle keep-alive heartbeat ping to prevent timeouts on 2+ hour chats
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            chat_item = {
                "type": "chat",
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            room.messages.append(chat_item)
            await room.broadcast(chat_item)
    except WebSocketDisconnect:
        if username in room.connections:
            del room.connections[username]
        leave_msg = {
            "type": "system",
            "sender": "System",
            "content": f"{username} left the chat.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        room.messages.append(leave_msg)
        await room.broadcast(leave_msg)
        await room.broadcast_users()

@app.websocket("/ws/{username}")
async def legacy_websocket_endpoint(websocket: WebSocket, username: str):
    await websocket_room_endpoint(websocket, "general", username)

# --- Serve Frontend Web UI ---
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
    print("  Burp Suite Chat Lab Server (4-Digit PIN Rooms)")
    print("  Local access:    http://127.0.0.1:8000")
    print("  Network access:  http://0.0.0.0:8000")
    print("  Press Ctrl + C to stop.")
    print("==================================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
