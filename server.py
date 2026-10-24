import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="Burp Suite Chat Lab Server")

# --- Room & Connection Management ---

class Room:
    def __init__(self, room_id: str, room_name: str, password: Optional[str] = None):
        self.room_id = room_id
        self.room_name = room_name
        self.password = password or ""  # empty means no password required
        self.connections: Dict[str, WebSocket] = {}
        self.messages: List[Dict] = []

    def check_password(self, pwd: Optional[str]) -> bool:
        if not self.password:
            return True
        return self.password == (pwd or "")

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
        # Create default public room
        self.rooms["general"] = Room("general", "General Public Chat", "")

    def get_or_create(self, room_id: str, name: str = "", password: str = "") -> Room:
        if room_id not in self.rooms:
            self.rooms[room_id] = Room(room_id, name or room_id, password)
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

manager = RoomManager()

# --- Pydantic Request Models ---

class CreateRoomRequest(BaseModel):
    room_id: str
    room_name: Optional[str] = None
    password: Optional[str] = None

class VerifyRoomRequest(BaseModel):
    room_id: str
    password: Optional[str] = None

class RoomChatMessage(BaseModel):
    sender: str
    content: str
    password: Optional[str] = None

# --- REST Endpoints (Great for Burp Suite Interception & Testing) ---

@app.post("/api/rooms/create")
async def create_room(req: CreateRoomRequest):
    """
    Create a new private or password-protected chat room.
    Burp exercise: inspect if passwords or room metadata are handled properly.
    """
    clean_id = req.room_id.strip().lower()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Room ID cannot be empty")
    
    if clean_id in manager.rooms:
        return {"status": "exists", "room_id": clean_id, "message": "Room already exists"}

    name = req.room_name.strip() if req.room_name else clean_id
    pwd = req.password.strip() if req.password else ""
    room = Room(room_id=clean_id, room_name=name, password=pwd)
    manager.rooms[clean_id] = room

    return {
        "status": "created",
        "room_id": clean_id,
        "room_name": name,
        "is_protected": bool(pwd)
    }

@app.post("/api/rooms/verify")
async def verify_room(req: VerifyRoomRequest):
    """
    Verify if a room exists and password matches before joining.
    Burp exercise: Test authentication bypass or brute-forcing room passwords!
    """
    clean_id = req.room_id.strip().lower()
    room = manager.get_room(clean_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not room.check_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid room password")

    return {
        "status": "authorized",
        "room_id": room.room_id,
        "room_name": room.room_name,
        "is_protected": bool(room.password)
    }

@app.get("/api/rooms/{room_id}/messages")
async def get_room_messages(room_id: str, password: Optional[str] = None):
    """
    Retrieve message history for a specific room.
    Burp exercise: Test IDOR by changing room_id to read other private chats!
    """
    room = manager.get_room(room_id.lower())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.check_password(password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"room_id": room.room_id, "messages": room.messages}

@app.post("/api/rooms/{room_id}/send")
async def send_room_message(room_id: str, msg: RoomChatMessage, request: Request):
    """
    Send a message via HTTP POST into a specific room.
    Burp exercise: Tamper with sender identity or room_id parameters!
    """
    room = manager.get_room(room_id.lower())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.check_password(msg.password):
        raise HTTPException(status_code=401, detail="Unauthorized")

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

@app.delete("/api/rooms/{room_id}/messages")
async def clear_room_messages(room_id: str, password: Optional[str] = None):
    room = manager.get_room(room_id.lower())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.check_password(password):
        raise HTTPException(status_code=401, detail="Unauthorized")

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
async def legacy_send_message(msg: RoomChatMessage, request: Request):
    return await send_room_message("general", msg, request)

@app.get("/api/users")
async def legacy_get_users():
    room = manager.get_room("general")
    return {"active_users": list(room.connections.keys()) if room else []}

# --- WebSocket Room Endpoint ---

@app.websocket("/ws/{room_id}/{username}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str, username: str, password: Optional[str] = Query(default=None)):
    clean_id = room_id.lower()
    room = manager.get_room(clean_id)
    
    # If room doesn't exist or password mismatch, reject connection
    if not room:
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": "Room not found. Please create it first."})
        await websocket.close(code=4004)
        return
        
    if not room.check_password(password):
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": "Unauthorized: Incorrect room password."})
        await websocket.close(code=4001)
        return

    await websocket.accept()
    room.connections[username] = websocket

    join_msg = {
        "type": "system",
        "sender": "System",
        "content": f"{username} joined the room.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    room.messages.append(join_msg)
    await room.broadcast(join_msg)
    await room.broadcast_users()

    try:
        while True:
            data = await websocket.receive_json()
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
            "content": f"{username} left the room.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        room.messages.append(leave_msg)
        await room.broadcast(leave_msg)
        await room.broadcast_users()

# Legacy single-room WebSocket endpoint
@app.websocket("/ws/{username}")
async def legacy_websocket_endpoint(websocket: WebSocket, username: str):
    await websocket_room_endpoint(websocket, "general", username)

# --- Serve Static UI ---
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
    print("  Burp Suite Chat Lab Server (With Private Rooms)")
    print("  Local access:    http://127.0.0.1:8000")
    print("  Network access:  http://0.0.0.0:8000")
    print("  Press Ctrl + C to stop.")
    print("==================================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
