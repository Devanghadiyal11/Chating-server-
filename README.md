# 💬 Chating room (Full Documentation)

A modern, full-featured multi-client real-time chat application built with **FastAPI**, **WebSockets**, and a responsive **Web UI**. Designed both for real-world usage across desktop/mobile browsers and as an interactive security lab for mastering **Burp Suite** (HTTP interception, tampering, Repeater, Intruder PIN brute-forcing, and WebSocket inspection).

---

## 📑 Table of Contents
1. [Key Features & Functionalities](#-key-features--functionalities)
2. [Mobile vs Desktop Experience](#-mobile-vs-desktop-experience)
3. [Architecture & Reliability](#-architecture--reliability)
4. [Project Structure](#-project-structure)
5. [Getting Started (Local & LAN)](#-getting-started-local--lan)
6. [Cloud Deployment (Vercel & Render)](#-cloud-deployment-vercel--render)
7. [Hands-On Burp Suite Practice Lab](#-hands-on-burp-suite-practice-lab)
8. [Python CLI Client (`client.py`)](#-python-cli-client-clientpy)
9. [REST & WebSocket API Reference](#-rest--websocket-api-reference)

---

## 🌟 Key Features & Functionalities

### 1. 🎲 4-Digit Auto-Generated PIN Rooms
- **Instant Creation:** Create private chat rooms with a single click. The server auto-generates a unique **4-digit numeric PIN** (e.g., `8492`).
- **Simple Room Joining:** Other users simply enter their username and the 4-digit PIN to join that exact private room.
- **Room Isolation:** Messages are strictly isolated. Users in room `1234` cannot see or receive messages from room `5678`.

### 2. 👑 Host Role & Room Lifecycle Management
- **Host Designation:** The user who generates the 4-digit PIN is marked as the room **Host** (`👑 Host`).
- **Persistent Stability:** Rooms stay alive even if the host's device sleeps, locks, switches apps, or reloads. Users can seamlessly reconnect without losing the conversation.
- **Explicit Room Deletion:** The host has an exclusive **"🛑 Delete Room"** control in the sidebar footer to terminate the room on demand. When clicked, all connected participants are notified and redirected back to the home lobby.

### 3. 👥 Live Active Users Sync ("Users In This Room")
- **Dual-Mode Tracking:** Real-time online user tracking that functions identically over **both HTTP mode and WebSocket mode**.
- **Live User Badges:**
  - 🟢 **Online status dot** for active participants.
  - **`👑 Host`** badge next to the room creator.
  - **`(You)`** badge next to your own nickname.
- **Live Counter:** Automatic participant count badge (e.g. `👥 2 online`) that updates whenever someone joins or leaves.
- **Automatic Inactivity Cleanup:** Users who close their tab or disconnect are automatically pruned from the online list after 25 seconds of inactivity.

### 4. ⏱️ Strict Chronological Message Ordering
- **Millisecond Timestamping (`time_ms`):** Every message is timestamped with server-verified millisecond precision.
- **Smart Chronological Insertion:** If network latency or polling causes messages to arrive out of order, the client automatically inserts them into their exact chronological place (oldest at top $\rightarrow$ newest at bottom).
- **Message De-Duplication (`msg_id`):** Unique IDs prevent duplicate bubbles when switching between WebSockets and HTTP polling.

### 5. 🔀 Protocol Switcher (Default: HTTP POST Mode)
- **HTTP POST Mode (Default):** All messages are sent via standard `POST /api/rooms/{pin}/send` requests. Perfect for instant capture in **Burp Suite Proxy $\rightarrow$ HTTP history** and **Repeater**.
- **WebSocket Mode:** Switch to real-time full-duplex WebSocket frames (`/ws/{pin}/{user}`) to inspect raw bidirectional frames in **Burp Suite Proxy $\rightarrow$ WebSockets history**.

### 6. 📸 View-Only Photo Sharing & Anti-Leak Protections
- **Instant Photo Sharing:** Click the 📷 camera button to select photos from your device, computer, or camera roll.
- **Client-Side Compression:** Automatically resizes and optimizes photos via HTML5 Canvas before sending, producing lightweight (~40–80 KB) images with zero transfer lag.
- **Serverless & Cloud Friendly:** Base64 data-URL transmission guarantees photo sharing works on **Vercel, Render, Railway, local PC, and mobile** without needing local disk writes or S3 buckets.
- **Mobile Long-Press & Download Shield:** Photos cannot be downloaded or saved via long-press menus or right-clicks (`-webkit-touch-callout: none`, `user-select: none`, transparent security shield overlays, `draggable="false"`).
- **Secure Canvas Lightbox (No Raw Image Tags):** Fullscreen viewing renders pixels directly to HTML5 Canvas underneath an invisible touch shield, preventing "Save Image As" or inspect-element link extractions.
- **Dynamic Security Watermarks:** Photos and lightbox views are stamped with diagonal semi-transparent watermarks (`CONFIDENTIAL • VIEW ONLY • [USERNAME] • ROOM [PIN]`) to deter unauthorized external camera captures.
- **Anti-Screenshot Privacy Curtain:** If a mobile user switches apps, opens multitasking, or triggers window blur/visibility changes to capture content, the screen instantly blacks out with a privacy curtain.
- **Print & PDF Blocked:** `@media print` rules ensure page printing or saving to PDF completely hides all content.

### 7. ✍️ Auto Text Alignment & Multi-Line Smart Input
- **Smart Alignment for Long Text:** Messages with substantial text (multiple paragraphs, code blocks, or > 80 characters) automatically switch to clean justified block alignment (`text-align: justify; text-justify: inter-word; text-align-last: start`) to eliminate jagged edges while preserving natural reading flow.
- **Bidirectional Auto Detection (`dir="auto"`):** Automatically aligns English, Hindi, Urdu, Arabic, and other multilingual text to its correct natural reading direction.
- **Preserved Formatting & Word Wrapping:** Built with `white-space: pre-wrap;` and `overflow-wrap: anywhere;` so line breaks, code indentations, and long URLs never overflow or break UI bounds.
- **Right/Left Edge Alignment:** Your own messages, sender name, and timestamps align flush right to your avatar, while other participants' messages align flush left.
- **Auto-Expanding Input Box:** The input box automatically expands from a single line up to 120px tall as you type longer messages, with support for `Shift + Enter` to insert new lines and `Enter` to send.

---

## 📱 Mobile vs Desktop Experience

The interface automatically detects screen sizes and adapts:

### 🖥️ Desktop Experience (Security Lab View):
- **Full Sidebar:** Shows brand badge, active room PIN card with 1-click copy, current user card, and protocol mode selector.
- **Burp Intruder Cheat Sheet:** Quick test injection buttons for XSS (`<script>alert(1)</script>`), HTML tags (`<b>Important</b>`), SQLi probes (`' OR 1=1--`), and spoofed system messages.
- **Live Wire Payload Preview:** Real-time inspector bar displaying the exact HTTP method (`POST /api/rooms/6364/send`) and raw JSON payload as you type.

### 📱 Mobile Experience (Clean & Distraction-Free):
- **Clean Chat View:** All developer tools, attack cheat sheets, and JSON payload preview bars are **hidden**.
- **WhatsApp / Telegram Style:** Full-width bubbles, smooth touch scrolling, and minimal bottom input bar.
- **Slide-Out Off-Canvas Drawer (☰ Hamburger Menu):** Room settings, PIN sharing, and the full active user list slide smoothly from the left when tapping the **☰** button or the online users pill.
- **Tap-to-Copy:** Easily tap the `PIN: 6364` pill in the header to copy the room code to your clipboard.

---

## 🛡️ Architecture & Reliability

- **High-Concurrency Engine:** Built with Python `asyncio` and FastAPI. Idle connections consume virtually zero CPU.
- **12-Second Cloud Keep-Alive Heartbeat:** Sends a lightweight `{type: "ping"}` frame every 12 seconds to prevent reverse proxies (Cloudflare, Nginx, Render, AWS) from dropping idle connections.
- **Fast Silent Auto-Reconnect:** If connection flickers or drops, client auto-reconnects every 1.5 seconds.
- **Automatic Serverless Recovery:** On stateless/serverless platforms (like Vercel), if a request hits a newly booted container, the room is auto-recovered instead of failing with `404 Room not found`.

---

## 📁 Project Structure

```
├── server.py        # Central FastAPI server (Rooms, WebSocket hub, REST endpoints, auto-recovery)
├── client.py        # Python CLI client with --proxy flag for Burp Suite testing
├── static/
│   └── index.html   # Modern responsive Web Chat UI (Mobile-first, drawer, Burp tools)
├── requirements.txt # Python dependencies (fastapi, uvicorn, websockets, requests)
├── Procfile         # Production startup script for Render / Railway
├── .gitignore       # Python cache and environment exclusion
└── README.md        # Comprehensive documentation & Burp lab guide
```

---

## 🚀 Getting Started (Local & LAN)

### 1. Run Server Locally
```bash
python server.py
```
The server starts at: **`http://127.0.0.1:8000`**

### 2. Connect from Other Devices on Same Wi-Fi
The server binds to `0.0.0.0`, making it accessible across your local network:
1. Find your machine's local IP address (e.g., `192.168.1.50` or `172.23.218.89`).
2. Any phone, laptop, or tablet on the same Wi-Fi can open:
   ```
   http://YOUR_LOCAL_IP:8000
   ```

---

## ☁️ Cloud Deployment (Vercel & Render)

### Option A: Render.com (Recommended for Zero-Latency WebSockets)
1. Push code to your GitHub repo: `https://github.com/Devanghadiyal11/Chating-server-`.
2. On [Render.com](https://render.com), click **New +** $\rightarrow$ **Web Service** $\rightarrow$ select your repo.
3. Render automatically reads [`Procfile`](file:///e:/Project/Procfile) and deploys persistent WebSockets for free.

### Option B: Vercel (`vercel.app`)
- The server includes auto-recovery and 1.5s background HTTP polling so Vercel serverless containers seamlessly sync messages without requiring persistent sockets.

---

## 🎯 Hands-On Burp Suite Practice Lab

### 🧪 Exercise 1: Intercept & Tamper with a Message (HTTP Mode)
1. In the Web UI, ensure **HTTP POST Mode** is active (default).
2. In Burp Suite, open **Proxy** $\rightarrow$ **Intercept** and turn **"Intercept is on"**.
3. Send a message as **Alice**: `"Hello Bob!"`.
4. In Burp Suite, view the paused request:
   ```http
   POST /api/rooms/6364/send HTTP/1.1
   Host: 127.0.0.1:8000
   Content-Type: application/json

   {"msg_id":"m_12345","sender":"Alice","content":"Hello Bob!"}
   ```
5. Modify `"content"` to: `"I am transferring $1,000,000 to Bob"`.
6. Click **Forward**. Bob receives the modified message in real time!

---

### 🧪 Exercise 2: Sender Impersonation (Spoofing)
1. Turn **Intercept is on** in Burp Suite.
2. Send any message as **Bob**.
3. In Burp, tamper with the `"sender"` field:
   ```json
   {"sender": "Admin", "content": "Security alert: Server maintenance in 5 minutes."}
   ```
4. Click **Forward**. The chat broadcasts the message with sender identity `Admin`.

---

### 🧪 Exercise 3: Brute-Force 4-Digit Room PINs with Burp Intruder
Because private rooms use 4-digit numeric codes (`1000` to `9999`), you can simulate an authorization brute-force attack:
1. In Burp Suite, intercept a join request:
   ```http
   POST /api/rooms/join HTTP/1.1
   Content-Type: application/json

   {"pin":"1111","username":"Hacker"}
   ```
2. Right-click $\rightarrow$ **Send to Intruder** (<kbd>Ctrl</kbd> + <kbd>I</kbd>).
3. In Intruder, set payload position on PIN: `{"pin":"§1111§","username":"Hacker"}`.
4. Under **Payloads**, choose **Numbers**:
   - From: `1000`
   - To: `9999`
   - Step: `1`
5. Click **Start Attack**. Sort by **Status** or **Length** to discover valid active room PINs (`200 OK` vs `404 Not Found`).

---

### 🧪 Exercise 4: WebSocket Frame Inspection
1. In the Web UI sidebar, select **WebSocket Mode**.
2. In Burp Suite, open **Proxy** $\rightarrow$ **WebSockets history**.
3. Send messages in chat. You will see raw JSON frames flowing bidirectionally in real time.

---

## 💻 Python CLI Client (`client.py`)

Run terminal-based chat clients that route through Burp Suite:

```bash
# Normal client:
python client.py --user Alice --pin 6364

# Routed through local Burp Suite Proxy (127.0.0.1:8080):
python client.py --user Alice --pin 6364 --proxy http://127.0.0.1:8080

# Connect to deployed cloud server:
python client.py --user Alice --pin 6364 --server https://your-app.onrender.com
```

---

## 📡 REST & WebSocket API Reference

| Endpoint | Method | Parameters / Body | Description |
| :--- | :---: | :--- | :--- |
| `/api/rooms/create` | `POST` | `{"room_name": str, "creator": str, "custom_pin": str?}` | Generates a 4-digit PIN and registers a new room. |
| `/api/rooms/join` | `POST` | `{"pin": str, "username": str}` | Validates room PIN and returns room details. |
| `/api/rooms/{pin}/users` | `GET` | `?username=str` | Returns list of currently active users in room and host name. |
| `/api/rooms/{pin}/messages` | `GET` | `?username=str&since_id=str?` | Returns message history for that PIN room. |
| `/api/rooms/{pin}/send` | `POST` | `{"sender": str, "content": str, "msg_id": str?}` | Broadcasts a chat message into the specified room. |
| `/api/rooms/{pin}/close` | `POST` | `{"sender": str, "content": "close"}` | Host action: closes room and notifies participants. |
| `/api/rooms/{pin}/messages` | `DELETE` | — | Clears all message history in specified room. |
| `/ws/{pin}/{username}` | `WS` | — | Persistent bidirectional WebSocket connection for live chat. |
