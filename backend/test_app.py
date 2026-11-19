"""
Comprehensive Automated Test Suite for Our Space Couple Chat Server
Tests REST API, Couple Authentication, WebSockets, Photo Vault, Soft-Deletion,
Reactions, Nudges, Settings, Chat-Clear Boundaries, and Reconnection Logic.
"""

import os
import sys
import json
import time
from starlette.testclient import TestClient
from server import app, room, PRIVATE_PIN, settings_cache

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("[*] STARTING COUPLE SERVER COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    passed = 0
    total = 0

    def assert_test(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [+] PASS: {name}")
        else:
            print(f"  [-] FAIL: {name} - {details}")

    # Clean initial state
    client.delete("/api/messages")

    # --- 1. Root & Health API Status ---
    print("\n--- 1. Testing API Root & Health Endpoints ---")
    res = client.get("/")
    assert_test("GET / returns 200 OK", res.status_code == 200)
    data = res.json()
    assert_test("API service is 'Our Space API Server 💕'", "Our Space" in data.get("service", ""))
    assert_test("Frontend URL points to Vercel deployment", "vercel.app" in data.get("frontend", ""))

    res_health = client.get("/health")
    assert_test("GET /health returns 200 OK", res_health.status_code == 200)
    assert_test("Health status is 'healthy'", res_health.json().get("status") == "healthy")

    # --- 2. Couple Join & Authentication ---
    print("\n--- 2. Testing Couple Authentication ---")
    # Wrong PIN
    res_fail = client.post("/api/join", json={"pin": "0000", "username": "Him"})
    assert_test("Wrong PIN returns 401 Unauthorized", res_fail.status_code == 401)

    # Empty username
    res_empty = client.post("/api/join", json={"pin": PRIVATE_PIN, "username": ""})
    assert_test("Empty username returns 400 Bad Request", res_empty.status_code == 400)

    # Valid join - Him
    res_him = client.post("/api/join", json={"pin": PRIVATE_PIN, "username": "Him"})
    assert_test("Valid PIN for Him returns 200 OK", res_him.status_code == 200)
    him_data = res_him.json()
    assert_test("Him is authorized with session token", him_data.get("ok") is True and len(him_data.get("token", "")) > 10)

    # Valid join - Her
    res_her = client.post("/api/join", json={"pin": PRIVATE_PIN, "username": "girlfriend"})
    assert_test("Valid PIN for Her canonicalizes nickname to 'Her'", res_her.status_code == 200 and res_her.json().get("username") == "Her")

    # --- 3. Couple Settings Sync ---
    print("\n--- 3. Testing Couple Settings Sync ---")
    res_settings = client.get("/api/settings")
    assert_test("GET /api/settings returns 200 OK", res_settings.status_code == 200)
    settings_data = res_settings.json()
    assert_test("Settings contains couple_name and theme", "couple_name" in settings_data and "theme" in settings_data)

    # Update settings
    res_update = client.post("/api/settings", json={"theme": "sunset", "couple_name": "Test Couple Space 💕"})
    assert_test("POST /api/settings updates settings", res_update.status_code == 200 and res_update.json().get("settings", {}).get("theme") == "sunset")

    # Revert settings to default
    client.post("/api/settings", json={"theme": "romantic", "couple_name": "Our Sweet Space 💕"})

    # --- 4. Message Sending (Text, Photo, Reply-To Quote) ---
    print("\n--- 4. Testing Message Sending (Text, Photo Base64, Quoted Reply) ---")
    msg1_payload = {
        "msg_id": "test_msg_1",
        "sender": "Him",
        "content": "Good morning my love! ❤️"
    }
    res_msg1 = client.post("/api/send", json=msg1_payload)
    assert_test("Him sends standard text message", res_msg1.status_code == 200 and res_msg1.json().get("status") == "ok")

    # Photo message
    dummy_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    msg2_payload = {
        "msg_id": "test_msg_2",
        "sender": "Her",
        "content": "Look at this picture!",
        "image": dummy_base64
    }
    res_msg2 = client.post("/api/send", json=msg2_payload)
    assert_test("Her sends photo message with base64 image", res_msg2.status_code == 200 and res_msg2.json().get("status") == "ok")

    # Quoted Swipe-to-Reply Message
    msg3_payload = {
        "msg_id": "test_msg_3",
        "sender": "Him",
        "content": "You look beautiful!",
        "reply_to": {
            "id": "test_msg_2",
            "sender": "Her",
            "content": "Look at this picture!"
        }
    }
    res_msg3 = client.post("/api/send", json=msg3_payload)
    assert_test("Him replies with quoted reply_to structure", res_msg3.status_code == 200 and res_msg3.json().get("status") == "ok")
    data_msg3 = res_msg3.json().get("message", {})
    assert_test("reply_to is preserved on message", data_msg3.get("reply_to", {}).get("id") == "test_msg_2")

    # --- 5. Message History & Delta Polling ---
    print("\n--- 5. Testing Message History & Delta Polling ---")
    res_msgs = client.get("/api/messages")
    assert_test("GET /api/messages returns 200 OK", res_msgs.status_code == 200)
    msgs = res_msgs.json().get("messages", [])
    assert_test("Chat stream has at least 3 messages", len(msgs) >= 3)

    # Delta Polling with since_id
    res_delta = client.get("/api/messages?since_id=test_msg_1")
    delta_msgs = res_delta.json().get("messages", [])
    assert_test("Delta polling with since_id=test_msg_1 returns subsequent messages", any(m["id"] == "test_msg_2" for m in delta_msgs))

    # --- 6. Reactions and Love Ping (Nudge) ---
    print("\n--- 6. Testing Reactions & Love Ping ---")
    res_rx = client.post("/api/reaction", json={"msg_id": "test_msg_1", "emoji": "💖", "sender": "Her"})
    assert_test("Her reacts to Him's message with 💖", res_rx.status_code == 200 and res_rx.json().get("status") == "ok")

    res_nudge = client.post("/api/nudge", json={"sender": "Him"})
    assert_test("Him sends Love Ping / Nudge", res_nudge.status_code == 200 and res_nudge.json().get("status") == "ok")

    # --- 7. Dedicated Photo Vault & Chat Clear Boundary ---
    print("\n--- 7. Testing Photo Vault & Server-Controlled Clear Boundary ---")
    # Verify photo exists in Vault
    res_vault_before = client.get("/api/images?include_cleared=true")
    assert_test("GET /api/images returns photo in Vault", res_vault_before.status_code == 200)
    imgs_before = res_vault_before.json().get("images", [])
    assert_test("Vault has at least 1 photo", len(imgs_before) >= 1)

    # Clear chat
    res_clear = client.delete("/api/messages")
    assert_test("DELETE /api/messages returns 200 with clear boundary", res_clear.status_code == 200 and res_clear.json().get("photos_soft_deleted_and_stored") is True)
    clear_data = res_clear.json()
    clear_seq = clear_data.get("cleared_before_seq")
    clear_ms = clear_data.get("cleared_at_ms")
    assert_test("Clear response contains valid boundary sequence & timestamp", clear_seq is not None and clear_seq > 0 and clear_ms is not None and clear_ms > 0)

    # Chat stream should now be completely empty
    res_msgs_after = client.get("/api/messages")
    msgs_after = res_msgs_after.json().get("messages", [])
    assert_test("Chat stream is now empty (0 messages)", len(msgs_after) == 0)
    assert_test("GET /api/messages returns updated clear boundary", res_msgs_after.json().get("cleared_before_seq") == clear_seq)

    # Catch-up events (/api/events?after_seq=0) MUST NOT leak cleared messages
    res_ev_after = client.get("/api/events?after_seq=0")
    assert_test("GET /api/events returns 200 OK", res_ev_after.status_code == 200)
    ev_list = res_ev_after.json().get("events", [])
    has_cleared_msg_events = any(e.get("type") == "message.created" for e in ev_list)
    assert_test("GET /api/events?after_seq=0 does NOT return cleared message.created events", not has_cleared_msg_events)

    # Vault STILL preserves photos because of soft-deletion
    res_vault_after = client.get("/api/images?include_cleared=true")
    imgs_after = res_vault_after.json().get("images", [])
    assert_test("Photo Vault STILL contains photos after clear chat (soft-deleted)", len(imgs_after) >= 1)

    # --- 8. Post-Clear Sending & Non-Reappearance ---
    print("\n--- 8. Testing Post-Clear New Message Sending & Non-Reappearance ---")
    msg4_payload = {
        "msg_id": "test_msg_post_clear",
        "sender": "Him",
        "content": "A brand new start after clear! ✨"
    }
    res_msg4 = client.post("/api/send", json=msg4_payload)
    assert_test("Him sends new message post-clear", res_msg4.status_code == 200 and res_msg4.json().get("status") == "ok")

    # Fetch messages again: MUST show ONLY the new message, never old messages
    res_msgs_new = client.get("/api/messages")
    msgs_new = res_msgs_new.json().get("messages", [])
    assert_test("Active chat conversation contains exactly 1 message", len(msgs_new) == 1)
    assert_test("Active chat message is the new post-clear message", msgs_new[0]["content"] == "A brand new start after clear! ✨")

    # Old delta query (e.g. asking for since_id=test_msg_1) MUST NOT resurrect cleared messages
    res_stale_delta = client.get("/api/messages?since_id=test_msg_1")
    stale_delta_msgs = res_stale_delta.json().get("messages", [])
    assert_test("Stale delta query returns ONLY post-clear message", len(stale_delta_msgs) == 1 and stale_delta_msgs[0]["id"] == "test_msg_post_clear")

    # --- 9. Multiple Clear Operations in Succession ---
    print("\n--- 9. Testing Multiple Clear Operations in Succession ---")
    res_clear2 = client.delete("/api/messages")
    clear_seq2 = res_clear2.json().get("cleared_before_seq")
    assert_test("Second clear succeeds with strictly monotonic boundary", clear_seq2 > clear_seq)

    res_msgs_after2 = client.get("/api/messages")
    assert_test("Chat is empty after second clear", len(res_msgs_after2.json().get("messages", [])) == 0)

    # Send after second clear
    client.post("/api/send", json={"msg_id": "msg_final", "sender": "Her", "content": "Clean state confirmed!"})
    res_msgs_final = client.get("/api/messages")
    assert_test("Only message sent after second clear appears", len(res_msgs_final.json().get("messages", [])) == 1 and res_msgs_final.json().get("messages", [])[0]["id"] == "msg_final")

    # --- 10. WebSocket Connection Lifecycle ---
    print("\n--- 10. Testing WebSocket Lifecycle (Ping/Pong, Presence, Messages) ---")
    try:
        with client.websocket_connect("/ws/Him") as ws:
            # Drain initial handshake events (users_update, theme_update, settings_update)
            initial_events = []
            for _ in range(3):
                evt = ws.receive_json()
                initial_events.append(evt.get("type"))
            assert_test("WebSocket connects and receives handshake events (users_update, theme, settings)", "users_update" in initial_events)

            # Test Keep-alive Heartbeat Ping/Pong
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert_test("WebSocket responds to ping with pong heartbeat", pong.get("type") == "pong")

            # Send WS message
            ws.send_json({
                "type": "chat",
                "msg_id": "ws_test_msg",
                "sender": "Him",
                "content": "Hello via WebSocket!"
            })
            ws_reply = ws.receive_json()
            is_valid_broadcast = (
                (ws_reply.get("type") == "event" and ws_reply.get("event", {}).get("payload", {}).get("content") == "Hello via WebSocket!") or
                ws_reply.get("content") == "Hello via WebSocket!"
            )
            assert_test(
                "WebSocket broadcasts message.created event with content",
                is_valid_broadcast,
                f"Received: {ws_reply}"
            )
    except Exception as e:
        assert_test("WebSocket lifecycle", False, str(e))

    # --- Clean up after test ---
    client.delete("/api/messages")

    # --- Summary ---
    print("\n" + "=" * 70)
    print(f"[+] TEST RESULTS SUMMARY: {passed} / {total} Passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
