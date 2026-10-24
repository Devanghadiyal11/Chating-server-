# 🛡️ Burp Suite Multi-Client Chat Lab

A complete server and multi-client chat lab specifically built to learn and practice **Burp Suite** (HTTP interception, tampering, Repeater, Intruder, and WebSocket inspection).

---

## 📁 Project Structure

```
e:\Project\
├── server.py        # Central FastAPI server handling REST & WebSocket chat broadcast
├── client.py        # Python CLI client with optional Burp Proxy support (--proxy)
├── static/
│   └── index.html   # Web chat frontend supporting both HTTP POST & WebSocket modes
└── README.md        # Hands-on Burp Suite practice guide
```

---

## 🚀 Step 1: Start the Chat Server

Open your terminal in `e:\Project` and run:

```bash
python server.py
```

The server will start at: **`http://127.0.0.1:8000`**

---

## 🌐 Step 2: Open Clients in Burp Suite

The easiest way to intercept traffic with zero proxy configuration is using **Burp Suite's Built-in Chromium Browser**:

1. Open **Burp Suite**.
2. Go to the **Proxy** tab -> **Intercept** sub-tab.
3. Click the **"Open Browser"** button (Burp's pre-configured browser).
4. In that browser, open **two separate tabs** or windows:
   - Tab 1: `http://127.0.0.1:8000` (Join as **Alice**)
   - Tab 2: `http://127.0.0.1:8000` (Join as **Bob**)

Now, any message sent between Alice and Bob will flow directly through Burp Suite!

---

## 🎯 Hands-On Burp Suite Practice Exercises

### 🧪 Exercise 1: Intercept & Tamper with a Message (HTTP Mode)

1. In the Web UI, select the **"HTTP POST"** mode radio button.
2. In Burp Suite, go to **Proxy** -> **Intercept** and click **"Intercept is off"** to turn it **ON** (`Intercept is on`).
3. Back in the chat UI as **Alice**, type:
   ```
   Hello Bob!
   ```
   and click **Send**.
4. Switch to Burp Suite. You will see the paused HTTP request:
   ```http
   POST /api/send HTTP/1.1
   Host: 127.0.0.1:8000
   Content-Type: application/json

   {"sender":"Alice","content":"Hello Bob!"}
   ```
5. **Modify the content** inside Burp Suite to:
   ```json
   {"sender":"Alice","content":"I am giving Bob $1,000,000!"}
   ```
6. Click **Forward** and turn **Intercept is off**.
7. Check Bob's chat screen: Bob receives the altered message!

---

### 🧪 Exercise 2: User Impersonation / Spoofing

1. Ensure **HTTP POST** mode is active.
2. Turn **Intercept is on** in Burp.
3. Send a message as **Alice**: `"Testing message"`.
4. In Burp Suite, change `"sender": "Alice"` to `"sender": "Admin"` or `"sender": "Bob"`.
5. Click **Forward**.
6. Observe how the server trusts the client-supplied `sender` parameter and broadcasts it to everyone as `Admin`.

---

### 🧪 Exercise 3: Burp Repeater (Message Replay)

1. In Burp Suite, open **Proxy** -> **HTTP history**.
2. Find any `POST /api/send` request.
3. Right-click it and select **"Send to Repeater"** (or press `Ctrl + R`).
4. Switch to the **Repeater** tab.
5. Edit the JSON body or headers as much as you want and click **Send**.
6. Every time you click **Send**, watch the server broadcast the message to all connected clients in real-time.

---

### 🧪 Exercise 4: WebSocket Interception & History

1. In the Web UI, select the **"WebSocket"** mode radio button.
2. In Burp Suite, go to **Proxy** -> **WebSockets history**.
3. Send a few messages in chat.
4. Click on the entries in **WebSockets history** to see the raw bidirectional JSON frames flowing between the browser and server.
5. In Burp, go to **Proxy** -> **Proxy settings** -> **WebSocket interception rules** to enable intercepting WebSocket messages in real-time.

---

### 🧪 Exercise 5: Using the Python CLI Client with Burp Proxy

You can also run client scripts that route their traffic through Burp Suite:

```bash
# Terminal 1 (Direct or Proxied Client):
python client.py --user Charlie --proxy http://127.0.0.1:8080
```

All HTTP requests made by `client.py` will appear inside Burp Suite's **HTTP history** tab!
