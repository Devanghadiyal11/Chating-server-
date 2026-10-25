# 💑 Our Sweet Space — Private Couple's Chat

A private, secure, and romantic real-time chat application built exclusively for two people. Powered by **FastAPI**, **WebSockets**, **MongoDB Atlas**, and an aesthetic mobile-first **Web UI**.

---

## 🌟 Key Features

### 1. 🔒 Dedicated 2-Person Sanctuary
- **Hardcoded Secret PIN (`1012`):** Only you and your girlfriend can enter.
- **Strict 2-User Capacity:** Any third party attempting to join is blocked (`403 Forbidden`).
- **1-Tap Direct Invite Link:** Pre-fills the secret PIN so your partner can join instantly from her phone without typing credentials.
- **Auto-Login & "Remember Me":** Seamlessly re-opens straight into your conversation whenever you visit the app.

### 2. 🎙️ Voice Notes & Audio Messages
- Native browser recording with live timer and pulsating indicator.
- Custom interactive audio bubble with play/pause, animated waveform frequencies, and duration display.
- Cancel or send with a single tap.

### 3. 💖 Double-Tap Love Reactions & Floating Hearts
- **Double-Tap Bubble:** Double-tap or double-click any message to burst floating hearts across the screen and add a ❤️ reaction.
- **Emoji Reaction Picker:** Hover or tap to choose from ❤️, 🥰, 😂, 🥺, 🔥.
- Real-time reaction synchronization.

### 4. 🔔 "Thinking of You" Love Nudge
- Tap the 💖 button anytime to send an instant love ping.
- The other person's screen explodes with floating hearts, sparkles, a gentle romantic sound chime, and haptic vibration feedback.

### 5. ⏳ Days Together Counter & Anniversary Tracker
- Header and sidebar show your love milestone (e.g. *"Together 412 Days 💕"*).
- Click to set or update your special anniversary date.

### 6. 🕵️ Stealth / Panic Disguise Mode
- Tap the 🕵️ button or press **`Escape`** anywhere.
- Instantly swaps the tab title, favicon, and screen to a realistic **Google Docs meeting notes workspace**, completely hiding the chat if someone walks by.
- Press `Escape` again to return to your chat.

### 7. 📸 View-Only Photo Sharing & Anti-Leak Shield
- Instant photo upload with client-side canvas compression.
- View-only canvas lightbox: disables right-click, image dragging, long-press save, and URL inspection.
- **Anti-Screenshot Privacy Curtain:** If multitasking is opened or the tab loses focus, the screen immediately blacks out until you resume.

### 8. 🎨 5 Romantic Themes & Wallpapers
- 🌸 **Rose Blossom** (Default romantic rose gold & dark velvet)
- 💜 **Midnight Lavender** (Deep purple nebula with violet glow)
- 🌅 **Sunset Warmth** (Warm terracotta, coral & espresso)
- 🌙 **OLED Noir** (Pure AMOLED black with neon heart pink)
- ☁️ **Cozy Cream** (Warm soft light mode)

### 9. 💬 Disappearing Messages
- Configure conversations to keep forever, or auto-prune after 1 hour or 24 hours.

### 10. ⚡ Live Typing Indicator & Offline Audio Synthesizer
- See when your partner is typing in real time.
- Built-in Web Audio API synthesizer generates soft bell tones and chimes with zero external audio files.

---

## 📁 Project Architecture (2 Main Folders)

```
Server/
├── backend/                  # 1. FastAPI & WebSocket Server
│   ├── server.py             # App, WebSocket hub, Monotonic seq, MongoDB sync
│   ├── client.py             # CLI test client
│   ├── test_app.py           # Test suite
│   ├── requirements.txt      # Python dependencies
│   ├── Procfile              # Render deployment configuration
│   ├── static/               # Legacy static web UI fallback
│   └── uploads/              # Media attachment storage
│
├── frontend/                 # 2. Next.js 16 Modern Client (Deploy on Vercel)
│   ├── src/
│   │   ├── app/              # App Router (page.tsx, layout.tsx, globals.css)
│   │   ├── components/       # Header, ChatInput, MessageList, QuickBar, Modals
│   │   └── lib/              # Types, Audio, IndexedDB offline queue, Config
│   ├── public/               # manifest.json, icon.svg, PWA assets
│   ├── package.json          # Dependencies & scripts
│   └── next.config.ts        # Next.js configuration
│
├── Procfile                  # Root Render runner
├── requirements.txt          # Root Python dependencies
└── README.md
```

---

## 🚀 Running the Project

### 1. Run the Backend (`backend/`)
```bash
cd backend
pip install -r requirements.txt
python server.py
```
* Runs on: `http://localhost:8000` (REST & WebSockets)

### 2. Run the Frontend (`frontend/`)
```bash
cd frontend
npm install
npm run dev
```
* Runs on: `http://localhost:3000`

---

## ☁️ Deployment

* **Backend**: Deploy on [Render](https://render.com) using repository root or `backend/` directory.
* **Frontend**: Deploy on [Vercel](https://vercel.com) from `https://github.com/Devanghadiyal11/Chating-Frontend.git`.

---

## 📱 How to Use With Your Partner
1. Open `http://<your-server-ip>:8000` or your deployed URL.
2. Enter your nickname and avatar emoji.
3. Click **"🔗 Copy Link for Her"** from the sidebar to send her the direct 1-tap link.
4. Enjoy your private, distraction-free space together! 💕
