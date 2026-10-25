"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { API_BASE, getWsUrl, getAuthHeaders } from "@/lib/config";
import {
  ChatMessage,
  CheckInDoc,
  TimelineEvent,
  OpenWhenLetter,
  ThemeType,
  MemoryItem,
  PendingMessage,
} from "@/lib/types";
import {
  savePendingMessage,
  getPendingMessages,
  removePendingMessage,
} from "@/lib/indexedDb";
import { playMessageChime, playLoveNudgeChime, burstHearts } from "@/lib/audio";
import { Header } from "@/components/Header";
import { QuickBar } from "@/components/QuickBar";
import { CheckinBanner } from "@/components/CheckinBanner";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar } from "@/components/Sidebar";

// Modals
import { ThemeModal } from "@/components/modals/ThemeModal";
import { CheckInModal } from "@/components/modals/CheckInModal";
import { TimelineModal } from "@/components/modals/TimelineModal";
import { LettersModal } from "@/components/modals/LettersModal";
import { LetterViewerModal } from "@/components/modals/LetterViewerModal";
import { WriteLetterModal } from "@/components/modals/WriteLetterModal";
import { MemoriesModal } from "@/components/modals/MemoriesModal";
import { PhotoLightboxModal } from "@/components/modals/PhotoLightboxModal";
import { AnniversaryModal } from "@/components/modals/AnniversaryModal";
import { LoginModal } from "@/components/modals/LoginModal";

export default function ChatPage() {
  const [mounted, setMounted] = useState(false);

  // Session & User
  const [currentUser, setCurrentUser] = useState("");
  const [currentAvatar, setCurrentAvatar] = useState("🐻");
  const [sessionToken, setSessionToken] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Room State
  const [coupleName, setCoupleName] = useState("Our Sweet Space 💕");
  const [anniversaryDate, setAnniversaryDate] = useState("2024-02-14");
  const [daysTogether, setDaysTogether] = useState(0);
  const [disappearingMode, setDisappearingMode] = useState(0);
  const [currentTheme, setCurrentTheme] = useState<ThemeType>("rose");
  const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Love Nudge Cooldown
  const [nudgeCooldown, setNudgeCooldown] = useState(0);

  // Messages & Modules State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [partnerCheckin, setPartnerCheckin] = useState<CheckInDoc | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [letters, setLetters] = useState<OpenWhenLetter[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);

  // Modals & Drawers
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [themeModalOpen, setThemeModalOpen] = useState(false);
  const [checkinModalOpen, setCheckinModalOpen] = useState(false);
  const [timelineModalOpen, setTimelineModalOpen] = useState(false);
  const [lettersModalOpen, setLettersModalOpen] = useState(false);
  const [writeLetterOpen, setWriteLetterOpen] = useState(false);
  const [activeLetter, setActiveLetter] = useState<OpenWhenLetter | null>(null);
  const [memoriesModalOpen, setMemoriesModalOpen] = useState(false);
  const [activePhoto, setActivePhoto] = useState<{ src: string; sender: string; time: string } | null>(null);
  const [anniversaryModalOpen, setAnniversaryModalOpen] = useState(false);

  // Stealth Disguise
  const [isStealth, setIsStealth] = useState(false);

  // Connection & Offline Queue
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "reconnecting" | "offline">("reconnecting");
  const [pendingCount, setPendingCount] = useState(0);

  // Reply Target State
  const [replyTarget, setReplyTarget] = useState<ChatMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const lastSeenIdRef = useRef<string | null>(null);
  const maxSeqRef = useRef<number>(0);

  // Refresh pending items count from IndexedDB
  const refreshPendingCount = useCallback(async () => {
    try {
      const items = await getPendingMessages();
      setPendingCount(items.length);
    } catch {}
  }, []);

  // Calculate days together
  const calcDays = useCallback((dateStr: string) => {
    const start = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor(Math.abs(now.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    setDaysTogether(diff);
  }, []);

  // Set theme helper
  const applyThemeStyle = (theme: ThemeType) => {
    setCurrentTheme(theme);
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", theme);
    }
  };

  // Initial Load from localStorage & Offline Queue check
  useEffect(() => {
    setMounted(true);
    refreshPendingCount();

    const savedUser = localStorage.getItem("couple_user");
    const savedToken = localStorage.getItem("couple_token");
    const savedAv = localStorage.getItem("couple_avatar") || "🐻";
    const savedTheme = (localStorage.getItem("couple_theme") as ThemeType) || "rose";

    applyThemeStyle(savedTheme);

    if (savedUser && savedToken) {
      setCurrentUser(savedUser);
      setSessionToken(savedToken);
      setCurrentAvatar(savedAv);
      setIsLoggedIn(true);
    }

    const onOnline = () => setConnectionStatus("reconnecting");
    const onOffline = () => setConnectionStatus("offline");
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [refreshPendingCount]);

  // Keyboard shortcut for Panic/Stealth mode
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsStealth((prev) => !prev);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Send ACK for partner's message
  const sendAck = useCallback((msgId: string, status: "delivered" | "seen" = "delivered") => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ack", msg_id: msgId, status }));
    } else {
      fetch(`${API_BASE}/api/ack`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ msg_id: msgId, status }),
      }).catch(() => {});
    }
  }, [sessionToken]);

  // Load chat history & missed messages using strict monotonic sequence or since_id
  const loadHistory = useCallback(async () => {
    if (!currentUser) return;
    try {
      let url = `${API_BASE}/api/messages?username=${encodeURIComponent(currentUser)}`;
      if (maxSeqRef.current > 0) {
        url += `&after_seq=${maxSeqRef.current}`;
      } else if (lastSeenIdRef.current) {
        url += `&since_id=${encodeURIComponent(lastSeenIdRef.current)}`;
      }
      const res = await fetch(url, { headers: getAuthHeaders(sessionToken) });
      if (res.ok) {
        const data = await res.json();
        const incoming: ChatMessage[] = data.messages || [];
        if (incoming.length > 0) {
          setMessages((prev) => {
            const map = new Map<string, ChatMessage>();
            prev.forEach((m) => {
              map.set(m.id, m);
              if (m.clientMessageId) map.set(m.clientMessageId, m);
            });
            incoming.forEach((m) => {
              map.set(m.id, m);
              if (m.clientMessageId) map.set(m.clientMessageId, m);
              lastSeenIdRef.current = m.id;
              if (m.seq) maxSeqRef.current = Math.max(maxSeqRef.current, m.seq);
              // Send ACK for incoming partner messages
              if (m.sender.toLowerCase() !== currentUser.toLowerCase()) {
                sendAck(m.id, "delivered");
              }
            });
            const list = Array.from(map.values());
            list.sort((a, b) => {
              if (a.seq && b.seq) return a.seq - b.seq;
              return (Number(a.time_ms) || 0) - (Number(b.time_ms) || 0);
            });
            return list;
          });
        }
      }
    } catch {
      // Offline fallback
    }
  }, [currentUser, sessionToken, sendAck]);

  // Load Checkin
  const loadCheckin = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/checkin`, { headers: getAuthHeaders(sessionToken) });
      if (res.ok) {
        const data = await res.json();
        const checkins: Record<string, CheckInDoc> = data.checkins || {};
        const myLower = currentUser.toLowerCase();
        let partnerDoc: CheckInDoc | null = null;
        for (const [key, doc] of Object.entries(checkins)) {
          if (key !== myLower) partnerDoc = doc;
        }
        setPartnerCheckin(partnerDoc);
      }
    } catch {}
  }, [currentUser, sessionToken]);

  // Load Timeline
  const loadTimeline = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/timeline`, { headers: getAuthHeaders(sessionToken) });
      if (res.ok) {
        const data = await res.json();
        setTimeline(data.timeline || []);
      }
    } catch {}
  }, [sessionToken]);

  // Load Letters
  const loadLetters = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/letters`, { headers: getAuthHeaders(sessionToken) });
      if (res.ok) {
        const data = await res.json();
        setLetters(data.letters || []);
      }
    } catch {}
  }, [sessionToken]);

  // Load Memories
  const loadMemories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/memories`, { headers: getAuthHeaders(sessionToken) });
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || []);
      }
    } catch {}
  }, [sessionToken]);

  // Load Settings
  const loadSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings`);
      if (res.ok) {
        const conf = await res.json();
        if (conf.couple_name) setCoupleName(conf.couple_name);
        if (conf.anniversary_date) {
          setAnniversaryDate(conf.anniversary_date);
          calcDays(conf.anniversary_date);
        }
        if (conf.disappearing_mode !== undefined) setDisappearingMode(conf.disappearing_mode);
        if (conf.theme) applyThemeStyle(conf.theme);
      }
    } catch {}
  }, [calcDays]);

  // Flush Outgoing Offline IndexedDB Queue
  const flushQueue = useCallback(async () => {
    try {
      const queue = await getPendingMessages();
      if (!queue.length) return;
      for (const item of queue) {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify(item));
          await removePendingMessage(item.clientMessageId);
          setMessages((prev) =>
            prev.map((m) => (m.clientMessageId === item.clientMessageId || m.id === item.clientMessageId ? { ...m, status: "sent" } : m))
          );
        } else {
          const res = await fetch(`${API_BASE}/api/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
            body: JSON.stringify(item),
          });
          if (res.ok) {
            await removePendingMessage(item.clientMessageId);
            setMessages((prev) =>
              prev.map((m) => (m.clientMessageId === item.clientMessageId || m.id === item.clientMessageId ? { ...m, status: "sent" } : m))
            );
          }
        }
      }
      refreshPendingCount();
    } catch (e) {
      console.warn("[Queue] Error flushing offline items:", e);
    }
  }, [sessionToken, refreshPendingCount]);

  // Connect WebSocket
  useEffect(() => {
    if (!isLoggedIn || !currentUser) return;

    let ws: WebSocket | null = null;
    let heartbeat: NodeJS.Timeout | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connect = () => {
      const url = getWsUrl(currentUser, sessionToken);
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus("connected");
        flushQueue();
        loadHistory();
        loadSettings();
        loadCheckin();
        loadTimeline();
        loadLetters();

        heartbeat = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 15000);
      };

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "pong") return;

          if (msg.type === "msg_status") {
            setMessages((prev) =>
              prev.map((m) => (m.id === msg.msg_id ? { ...m, status: msg.status } : m))
            );
            return;
          }

          if (msg.type === "partner_online") {
            // Auto mark sent as delivered
            setMessages((prev) =>
              prev.map((m) => (m.status === "sent" ? { ...m, status: "delivered" } : m))
            );
            return;
          }

          if (msg.type === "theme_update") {
            applyThemeStyle(msg.theme);
            if (msg.sender && msg.sender.toLowerCase() !== currentUser.toLowerCase()) {
              burstHearts(20);
            }
            return;
          }

          if (msg.type === "checkin_update") {
            loadCheckin();
            if (msg.checkin?.username?.toLowerCase() !== currentUser.toLowerCase()) {
              burstHearts(15);
            }
            return;
          }

          if (msg.type === "timeline_update" || msg.type === "timeline_delete") {
            loadTimeline();
            return;
          }

          if (msg.type === "letter_new" || msg.type === "letter_opened") {
            loadLetters();
            if (msg.type === "letter_new") burstHearts(20);
            return;
          }

          if (msg.type === "users_update") {
            setOnlineUsers(msg.users || []);
            return;
          }

          if (msg.type === "settings_update") {
            const conf = msg.settings || {};
            if (conf.couple_name) setCoupleName(conf.couple_name);
            if (conf.anniversary_date) {
              setAnniversaryDate(conf.anniversary_date);
              calcDays(conf.anniversary_date);
            }
            if (conf.theme) applyThemeStyle(conf.theme);
            return;
          }

          if (msg.type === "nudge") {
            burstHearts(40);
            playLoveNudgeChime(soundEnabled);
            return;
          }

          if (msg.type === "delete_message") {
            setMessages((prev) => prev.filter((m) => m.id !== msg.msg_id));
            return;
          }

          if (msg.type === "reaction_update") {
            setMessages((prev) =>
              prev.map((m) => (m.id === msg.msg_id ? { ...m, reactions: msg.reactions } : m))
            );
            return;
          }

          // Regular chat / photo / audio message
          const chatItem: ChatMessage = msg;
          if (chatItem.seq) maxSeqRef.current = Math.max(maxSeqRef.current, chatItem.seq);

          setMessages((prev) => {
            const exists = prev.some((m) => m.id === chatItem.id || (chatItem.clientMessageId && m.clientMessageId === chatItem.clientMessageId));
            if (exists) {
              return prev.map((m) => (m.id === chatItem.id || (chatItem.clientMessageId && m.clientMessageId === chatItem.clientMessageId) ? { ...m, ...chatItem, status: "sent" } : m));
            }
            const updated = [...prev, chatItem];
            updated.sort((a, b) => {
              if (a.seq && b.seq) return a.seq - b.seq;
              return (Number(a.time_ms) || 0) - (Number(b.time_ms) || 0);
            });
            return updated;
          });

          // Remove from local IndexedDB queue if this was ours
          if (chatItem.clientMessageId) {
            removePendingMessage(chatItem.clientMessageId).then(() => refreshPendingCount());
          }

          if (chatItem.sender.toLowerCase() !== currentUser.toLowerCase()) {
            sendAck(chatItem.id, "delivered");
            playMessageChime(soundEnabled);
          }
        } catch {}
      };

      ws.onclose = () => {
        setConnectionStatus(typeof navigator !== "undefined" && !navigator.onLine ? "offline" : "reconnecting");
        if (heartbeat) clearInterval(heartbeat);
        reconnectTimeout = setTimeout(() => connect(), 2000);
      };

      ws.onerror = () => {
        setConnectionStatus("reconnecting");
      };
    };

    connect();

    // Background Delta Polling (2.5s) for guaranteed background sync
    const pollInterval = setInterval(() => {
      loadHistory();
      flushQueue();
    }, 2500);

    return () => {
      if (ws) ws.close();
      if (heartbeat) clearInterval(heartbeat);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(pollInterval);
    };
  }, [isLoggedIn, currentUser, sessionToken, flushQueue, loadHistory, loadSettings, loadCheckin, loadTimeline, loadLetters, calcDays, sendAck, soundEnabled, refreshPendingCount]);

  // Login handler
  const handleLogin = async (name: string, pin: string, avatar: string, remember: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/api/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: name, pin }),
      });
      const data = await res.json();
      if (res.ok) {
        setCurrentUser(data.username);
        setSessionToken(data.token);
        setCurrentAvatar(avatar);
        setIsLoggedIn(true);

        if (remember) {
          localStorage.setItem("couple_user", data.username);
          localStorage.setItem("couple_token", data.token);
          localStorage.setItem("couple_avatar", avatar);
        }
        if (data.settings?.theme) applyThemeStyle(data.settings.theme);
        return { success: true };
      }
      return { success: false, error: data.detail || "Access denied" };
    } catch (e: unknown) {
      return { success: false, error: "Connection error: " + (e instanceof Error ? e.message : String(e)) };
    }
  };

  // Logout handler
  const handleLogout = () => {
    if (!confirm("Leave and lock your private chat?")) return;
    if (wsRef.current) wsRef.current.close();
    localStorage.removeItem("couple_user");
    localStorage.removeItem("couple_token");
    setIsLoggedIn(false);
    setCurrentUser("");
    setSessionToken("");
  };

  // Send Message
  const handleSendMessage = async (content: string, stagedPhoto: string | null) => {
    const clientMessageId = "m_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
    const nowMs = Date.now();
    const replyDoc = replyTarget
      ? {
          id: replyTarget.id,
          sender: replyTarget.sender,
          content: replyTarget.content,
          type: replyTarget.type,
        }
      : null;

    const payload: ChatMessage = {
      id: clientMessageId,
      clientMessageId,
      msg_id: clientMessageId,
      sender: currentUser,
      content,
      image: stagedPhoto,
      type: stagedPhoto ? "image" : "chat",
      timestamp: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
      time_ms: nowMs,
      reply_to: replyDoc,
      status: "pending",
      reactions: {},
    };

    // 0ms Optimistic render & clear reply preview
    setMessages((prev) => [...prev, payload]);
    setReplyTarget(null);

    // Save to durable IndexedDB queue
    await savePendingMessage(payload as PendingMessage);
    refreshPendingCount();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      setMessages((prev) =>
        prev.map((m) => (m.id === clientMessageId ? { ...m, status: "sent" } : m))
      );
    } else {
      fetch(`${API_BASE}/api/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify(payload),
      }).then(async (res) => {
        if (res.ok) {
          await removePendingMessage(clientMessageId);
          refreshPendingCount();
          setMessages((prev) =>
            prev.map((m) => (m.id === clientMessageId ? { ...m, status: "sent" } : m))
          );
        }
      }).catch(() => {});
    }
  };

  // Send Audio Note
  const handleSendAudio = async (audioBase64: string, durationSec: number) => {
    const clientMessageId = "m_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
    const nowMs = Date.now();
    const replyDoc = replyTarget
      ? {
          id: replyTarget.id,
          sender: replyTarget.sender,
          content: replyTarget.content,
          type: replyTarget.type,
        }
      : null;

    const payload: ChatMessage = {
      id: clientMessageId,
      clientMessageId,
      msg_id: clientMessageId,
      sender: currentUser,
      audio: audioBase64,
      audio_duration: durationSec,
      type: "audio",
      timestamp: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
      time_ms: nowMs,
      reply_to: replyDoc,
      status: "pending",
      reactions: {},
    };

    setMessages((prev) => [...prev, payload]);
    setReplyTarget(null);

    await savePendingMessage(payload as PendingMessage);
    refreshPendingCount();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      setMessages((prev) =>
        prev.map((m) => (m.id === clientMessageId ? { ...m, status: "sent" } : m))
      );
    } else {
      fetch(`${API_BASE}/api/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify(payload),
      }).then(async (res) => {
        if (res.ok) {
          await removePendingMessage(clientMessageId);
          refreshPendingCount();
          setMessages((prev) =>
            prev.map((m) => (m.id === clientMessageId ? { ...m, status: "sent" } : m))
          );
        }
      }).catch(() => {});
    }
  };

  // Love Nudge with 5s Cooldown
  const handleSendNudge = () => {
    if (nudgeCooldown > 0) return;
    setNudgeCooldown(5);
    burstHearts(30);
    playLoveNudgeChime(soundEnabled);

    const interval = setInterval(() => {
      setNudgeCooldown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "nudge" }));
    } else {
      fetch(`${API_BASE}/api/nudge`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ sender: currentUser }),
      });
    }
  };

  // Select Synced Theme
  const handleSelectTheme = (theme: ThemeType) => {
    applyThemeStyle(theme);
    burstHearts(18);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "theme_change", theme }));
    }
    fetch(`${API_BASE}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
      body: JSON.stringify({ theme }),
    }).catch(() => {});
  };

  // Toggle Reaction
  const handleToggleReaction = async (msgId: string, emoji: string) => {
    burstHearts(10);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "reaction", msg_id: msgId, emoji }));
    } else {
      fetch(`${API_BASE}/api/reaction`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ msg_id: msgId, emoji, sender: currentUser }),
      });
    }
  };

  // Delete Message
  const handleDeleteMessage = (msgId: string) => {
    if (!confirm("Delete this message for both of you?")) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "delete_message", msg_id: msgId }));
    } else {
      fetch(`${API_BASE}/api/messages/${encodeURIComponent(msgId)}`, {
        method: "DELETE",
        headers: getAuthHeaders(sessionToken),
      });
    }
    setMessages((prev) => prev.filter((m) => m.id !== msgId));
  };

  // Clear Chat
  const handleClearChat = async () => {
    if (!confirm("Clear all conversation history? This cannot be undone.")) return;
    try {
      await fetch(`${API_BASE}/api/messages`, {
        method: "DELETE",
        headers: getAuthHeaders(sessionToken),
      });
      setMessages([]);
      lastSeenIdRef.current = null;
    } catch {}
  };

  // Submit Checkin
  const handleSubmitCheckin = async (mood: string, note: string) => {
    burstHearts(20);
    try {
      const res = await fetch(`${API_BASE}/api/checkin`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ mood, note }),
      });
      if (res.ok) {
        loadCheckin();
      }
    } catch {}
  };

  // Add Milestone
  const handleAddMilestone = async (ev: Omit<TimelineEvent, "id">) => {
    burstHearts(16);
    try {
      const res = await fetch(`${API_BASE}/api/timeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify(ev),
      });
      if (res.ok) {
        loadTimeline();
      }
    } catch {}
  };

  // Delete Milestone
  const handleDeleteMilestone = async (id: string) => {
    if (!confirm("Delete this milestone?")) return;
    try {
      await fetch(`${API_BASE}/api/timeline/${encodeURIComponent(id)}`, {
        method: "DELETE",
        headers: getAuthHeaders(sessionToken),
      });
      setTimeline((prev) => prev.filter((x) => x.id !== id));
    } catch {}
  };

  // Submit Letter
  const handleSubmitLetter = async (title: string, content: string, hint: string) => {
    burstHearts(25);
    try {
      const res = await fetch(`${API_BASE}/api/letters`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ title, content, open_hint: hint }),
      });
      if (res.ok) {
        loadLetters();
        alert("Your letter has been sealed with wax and stored in your space! 💌");
      }
    } catch {}
  };

  // Select / Unseal Letter
  const handleSelectLetter = async (letter: OpenWhenLetter) => {
    if (letter.is_sealed !== false) {
      if (!confirm(`Are you ready to break the wax seal and open: "${letter.title}"? 💕`)) return;
      burstHearts(35);
      playLoveNudgeChime(soundEnabled);
      try {
        const res = await fetch(`${API_BASE}/api/letters/${encodeURIComponent(letter.id)}/open`, {
          method: "POST",
          headers: getAuthHeaders(sessionToken),
        });
        if (res.ok) {
          const d = await res.json();
          letter = d.letter || letter;
          loadLetters();
        }
      } catch {}
    }
    setActiveLetter(letter);
  };

  // Save Anniversary & Couple Name
  const handleSaveAnniversary = async (date: string, name: string) => {
    burstHearts(20);
    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ anniversary_date: date, couple_name: name }),
      });
      if (res.ok) {
        setAnniversaryDate(date);
        setCoupleName(name);
        calcDays(date);
      }
    } catch {}
  };

  // Change Disappearing Mode
  const handleChangeDisappearing = async (seconds: number) => {
    setDisappearingMode(seconds);
    try {
      await fetch(`${API_BASE}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders(sessionToken) },
        body: JSON.stringify({ disappearing_mode: seconds }),
      });
    } catch {}
  };

  if (!mounted) {
    return (
      <div className="flex w-full h-[100dvh] items-center justify-center bg-[#0c0a10] text-[#e11d48]">
        <span className="text-4xl animate-bounce">💖</span>
      </div>
    );
  }

  // Panic / Stealth Screen Disguise
  if (isStealth) {
    return (
      <div
        onClick={() => setIsStealth(false)}
        className="fixed inset-0 bg-white text-gray-900 p-8 font-sans z-50 flex flex-col justify-start select-none cursor-pointer"
      >
        <div className="flex items-center gap-2 border-b pb-3 mb-6">
          <span className="text-blue-600 font-bold text-xl">📄 Google Docs</span>
          <span className="text-gray-400 text-sm">| Q4 Performance Review & Team Sync Notes</span>
        </div>
        <div className="max-w-2xl text-sm leading-relaxed text-gray-700 space-y-4">
          <h1 className="text-xl font-bold text-gray-900">1. Executive Overview</h1>
          <p>The team achieved 98.4% of OKR milestones during Q4 with consistent throughput across the primary pipeline.</p>
          <h2 className="text-base font-semibold text-gray-800">2. Key Action Items</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Finalize cross-functional infrastructure migration plan.</li>
            <li>Review staging latency metrics ahead of client presentation.</li>
            <li>Schedule weekly sync for upcoming product release.</li>
          </ul>
        </div>
        <div className="mt-auto text-xs text-gray-400">Press ESC or tap anywhere to resume private space 💕</div>
      </div>
    );
  }

  return (
    <div className="flex w-full h-full h-[100dvh] overflow-hidden bg-[var(--bg-root)] text-[var(--text-main)]">
      {/* Login Modal */}
      <LoginModal isOpen={!isLoggedIn} onLogin={handleLogin} />

      {/* Sidebar Drawer */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        coupleName={coupleName}
        daysTogether={daysTogether}
        currentUser={currentUser}
        currentAvatar={currentAvatar}
        onlineUsers={onlineUsers}
        currentTheme={currentTheme}
        disappearingMode={disappearingMode}
        onSelectTheme={handleSelectTheme}
        onChangeDisappearing={handleChangeDisappearing}
        onOpenAnniversary={() => setAnniversaryModalOpen(true)}
        onOpenCheckIn={() => setCheckinModalOpen(true)}
        onOpenTimeline={() => setTimelineModalOpen(true)}
        onOpenLetters={() => setLettersModalOpen(true)}
        onOpenMemories={() => { loadMemories(); setMemoriesModalOpen(true); }}
        onClearChat={handleClearChat}
        onLogout={handleLogout}
      />

      {/* Main Chat Stream */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        <Header
          coupleName={coupleName}
          daysTogether={daysTogether}
          nudgeCooldown={nudgeCooldown}
          soundEnabled={soundEnabled}
          connectionStatus={connectionStatus}
          pendingCount={pendingCount}
          onOpenSidebar={() => setSidebarOpen(true)}
          onOpenAnniversary={() => setAnniversaryModalOpen(true)}
          onOpenThemeModal={() => setThemeModalOpen(true)}
          onSendNudge={handleSendNudge}
          onToggleSound={() => setSoundEnabled((prev) => !prev)}
          onToggleStealth={() => setIsStealth(true)}
        />

        <QuickBar
          currentTheme={currentTheme}
          onOpenThemeModal={() => setThemeModalOpen(true)}
          onOpenCheckIn={() => setCheckinModalOpen(true)}
          onOpenLetters={() => setLettersModalOpen(true)}
          onOpenTimeline={() => setTimelineModalOpen(true)}
          onOpenMemories={() => { loadMemories(); setMemoriesModalOpen(true); }}
        />

        <CheckinBanner
          partnerCheckin={partnerCheckin}
          onOpenCheckIn={() => setCheckinModalOpen(true)}
        />

        <MessageList
          messages={messages}
          currentUser={currentUser}
          onToggleReaction={handleToggleReaction}
          onDeleteMessage={handleDeleteMessage}
          onOpenPhoto={(src, sender, time) => setActivePhoto({ src, sender, time })}
          onReplyMessage={(msg) => setReplyTarget(msg)}
        />

        <ChatInput
          onSendMessage={handleSendMessage}
          onSendAudio={handleSendAudio}
          onSendNudge={handleSendNudge}
          nudgeCooldown={nudgeCooldown}
          replyTarget={replyTarget}
          onCancelReply={() => setReplyTarget(null)}
        />
      </main>

      {/* Modals */}
      <ThemeModal
        isOpen={themeModalOpen}
        onClose={() => setThemeModalOpen(false)}
        currentTheme={currentTheme}
        onSelectTheme={handleSelectTheme}
      />

      <CheckInModal
        isOpen={checkinModalOpen}
        onClose={() => setCheckinModalOpen(false)}
        partnerCheckin={partnerCheckin}
        onSubmitCheckin={handleSubmitCheckin}
      />

      <TimelineModal
        isOpen={timelineModalOpen}
        onClose={() => setTimelineModalOpen(false)}
        daysTogether={daysTogether}
        anniversaryDate={anniversaryDate}
        timeline={timeline}
        onAddMilestone={handleAddMilestone}
        onDeleteMilestone={handleDeleteMilestone}
      />

      <LettersModal
        isOpen={lettersModalOpen}
        onClose={() => setLettersModalOpen(false)}
        letters={letters}
        onSelectLetter={handleSelectLetter}
        onOpenWriteModal={() => setWriteLetterOpen(true)}
      />

      <LetterViewerModal
        letter={activeLetter}
        onClose={() => setActiveLetter(null)}
      />

      <WriteLetterModal
        isOpen={writeLetterOpen}
        onClose={() => setWriteLetterOpen(false)}
        onSubmitLetter={handleSubmitLetter}
      />

      <MemoriesModal
        isOpen={memoriesModalOpen}
        onClose={() => setMemoriesModalOpen(false)}
        memories={memories}
        onOpenPhoto={(src, sender, time) => setActivePhoto({ src, sender, time })}
      />

      <PhotoLightboxModal
        photo={activePhoto}
        onClose={() => setActivePhoto(null)}
      />

      <AnniversaryModal
        isOpen={anniversaryModalOpen}
        onClose={() => setAnniversaryModalOpen(false)}
        currentDate={anniversaryDate}
        currentName={coupleName}
        onSave={handleSaveAnniversary}
      />
    </div>
  );
}
