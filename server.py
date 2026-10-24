import asyncio
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="Burp Suite Chat Lab Server")

# In-memory storage for messages
messages_history: List[Dict] = []

# Connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket
        join_msg = {
            "type": "system",
            "sender": "System",
            "content": f"{username} joined the chat.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        messages_history.append(join_msg)
        await self.broadcast(join_msg)
        await self.broadcast_users()

    async def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]
            await self.broadcast_users()

    async def broadcast_users(self):
        msg = {
            "type": "users_update",
            "users": list(self.active_connections.keys())
        }
        await self.broadcast(msg)

    async def broadcast(self, message: dict):
        for username, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Data models for REST API
class ChatMessage(BaseModel):
    sender: str
    content: str

# 1. HTTP Endpoints (Great for Burp Proxy, Repeater, & Intruder)

@app.get("/api/messages")
async def get_messages():
    """Retrieve chat history via HTTP GET"""
    return {"messages": messages_history}

@app.delete("/api/messages")
async def clear_messages():
    """Reset lab chat history"""
    messages_history.clear()
    clear_msg = {
        "type": "system",
        "sender": "System",
        "content": "Chat history was cleared.",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await manager.broadcast(clear_msg)
    return {"status": "cleared"}

@app.post("/api/send")
async def send_message_http(msg: ChatMessage, request: Request):
    """
    Send a message via HTTP POST.
    Burp users can intercept this request to:
    - Change 'sender' to impersonate another client
    - Tamper with 'content'
    - Test header injections
    """
    chat_item = {
        "type": "chat",
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "client_ip": request.client.host if request.client else "unknown"
    }
    messages_history.append(chat_item)
    # Broadcast to all live WebSocket clients as well
    await manager.broadcast(chat_item)
    return {"status": "success", "message": chat_item}

@app.get("/api/users")
async def get_active_users():
    """List currently connected WebSocket users"""
    return {"active_users": list(manager.active_connections.keys())}

# 2. WebSocket Endpoint (Great for Burp WebSocket Intercept & WebSocket History)

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Burp Suite can intercept this WebSocket frame!
            chat_item = {
                "type": "chat",
                "sender": data.get("sender", username),
                "content": data.get("content", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            messages_history.append(chat_item)
            await manager.broadcast(chat_item)
    except WebSocketDisconnect:
        await manager.disconnect(username)
        leave_msg = {
            "type": "system",
            "sender": "System",
            "content": f"{username} left the chat.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        messages_history.append(leave_msg)
        await manager.broadcast(leave_msg)

# 3. Serve Frontend Web Chat UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Chat server is running. Web client UI not found.</h1>"

if __name__ == "__main__":
    print("==================================================================")
    print("  Burp Suite Chat Lab Server")
    print("  Local access:    http://127.0.0.1:8000")
    print("  Network access:  http://0.0.0.0:8000 (accessible on your LAN IP)")
    print("  Press Ctrl + C to stop the server.")
    print("==================================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
