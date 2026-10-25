export type ThemeType = "rose" | "lavender" | "sunset" | "noir" | "cream";

export type DeliveryStatus = "pending" | "sent" | "delivered" | "seen";

export interface ChatMessage {
  id: string;
  seq?: number;
  msg_id?: string;
  clientMessageId?: string;
  sender: string;
  content?: string;
  image?: string | null;
  audio?: string | null;
  audio_duration?: number;
  reply_to?: { id: string; sender: string; content?: string; type?: string } | null;
  type: "chat" | "image" | "audio" | "system";
  timestamp: string;
  time_ms: number;
  status?: DeliveryStatus;
  reactions?: Record<string, string[]>;
}

export interface PendingMessage {
  clientMessageId: string;
  sender: string;
  content?: string;
  image?: string | null;
  audio?: string | null;
  audio_duration?: number;
  reply_to?: { id: string; sender: string; content?: string; type?: string } | null;
  type: "chat" | "image" | "audio";
  time_ms: number;
  timestamp: string;
}

export interface CheckInDoc {
  username: string;
  date: string;
  mood: string;
  note?: string;
  updated_at: number;
}

export interface TimelineEvent {
  id: string;
  title: string;
  date: string;
  icon?: string;
  notes?: string;
}

export interface OpenWhenLetter {
  id: string;
  sender: string;
  title: string;
  content: string;
  open_hint?: string;
  is_sealed: boolean;
  opened_at?: number | null;
  created_at: number;
}

export interface CoupleSettings {
  anniversary_date: string;
  disappearing_mode: number;
  couple_name: string;
  theme: ThemeType;
}

export interface MemoryItem {
  id: string;
  type: "photo" | "audio";
  src: string;
  sender: string;
  time_ms: number;
  duration?: number;
}
