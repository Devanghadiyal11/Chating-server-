"""
Comprehensive Automated Test Suite for Chating room Application
Tests REST API, WebSockets, Delta Polling, Host Controls, Photo Security, and Static Assets.
"""

import re
import os
import sys
import json
import time
from starlette.testclient import TestClient
from server import app, manager

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("[*] STARTING FULL COMPREHENSIVE TEST SUITE")
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

    # --- 1. Static Asset & Frontend Integrity ---
    print("\n--- 1. Testing Frontend Static Assets & Security Markups ---")
    res = client.get("/")
    assert_test("GET / serves index.html with 200 OK", res.status_code == 200)
    html_content = res.text
    
    assert_test("Brand Title is 'Chating room'", "Chating room" in html_content)
    assert_test("Photo View-Only Security Shield is present", "photo-secure-wrapper" in html_content and "photo-shield" in html_content)
    assert_test("Secure Canvas Lightbox is present", "lightboxCanvas" in html_content and "lightbox-watermark" in html_content)
    assert_test("Anti-Screenshot Privacy Curtain is present", "privacyCurtain" in html_content)
    assert_test("Auto-Alignment for long text CSS is present", "auto-align-long" in html_content and "text-align: justify" in html_content)
    assert_test("Auto-expanding textarea is used for input", '<textarea' in html_content and 'id="chatInput"' in html_content)
    assert_test("Delta polling since_id parameter is implemented", "since_id" in html_content and "lastSeenMsgId" in html_content)

    # --- 2. Room Creation & 4-Digit PIN Generation ---
    print("\n--- 2. Testing Room Creation & PIN Logic ---")
    create_payload = {"room_name": "Test Security Room", "creator": "Alice"}
    res = client.post("/api/rooms/create", json=create_payload)
    assert_test("POST /api/rooms/create returns 200 OK", res.status_code == 200)
    data = res.json()
    pin = data.get("pin", "")
    assert_test("PIN is exactly 4 digits", len(pin) == 4 and pin.isdigit(), f"Received PIN: {pin}")
    assert_test("Host is Alice", data.get("host") == "Alice")
    assert_test("Room name is preserved", data.get("room_name") == "Test Security Room")

    # --- 3. Room Joining & Authentication ---
    print("\n--- 3. Testing Room Joining & Authentication ---")
    join_success = client.post("/api/rooms/join", json={"pin": pin, "username": "Bob"})
    assert_test("POST /api/rooms/join with correct PIN returns 200 OK", join_success.status_code == 200)
    join_data = join_success.json()
    assert_test("Join returns correct room info", join_data.get("pin") == pin and join_data.get("host") == "Alice")

    join_fail = client.post("/api/rooms/join", json={"pin": "99999", "username": "Eve"})
    assert_test("POST /api/rooms/join with invalid PIN returns 400 Bad Request", join_fail.status_code == 400)

    # --- 4. User Presence & Host Role Verification ---
    print("\n--- 4. Testing User Tracking & Host Tagging ---")
    users_res = client.get(f"/api/rooms/{pin}/users?username=Charlie")
    assert_test("GET /api/rooms/{pin}/users returns 200 OK", users_res.status_code == 200)
    users_data = users_res.json()
    assert_test("Charlie is in users list", "Charlie" in users_data.get("users", []))
    assert_test("Alice is designated host", users_data.get("host") == "Alice")

    # --- 5. Message Sending (Text, Photo Base64, Long Text) ---
    print("\n--- 5. Testing Message Sending (Text, Base64 Image, Long Text) ---")
    # Message 1: Normal text
    msg1_payload = {
        "msg_id": "m_test_1",
        "sender": "Alice",
        "content": "Hello Bob!"
    }
    res_msg1 = client.post(f"/api/rooms/{pin}/send", json=msg1_payload)
    assert_test("Alice sends standard text message", res_msg1.status_code == 200)

    # Message 2: Base64 View-Only Photo
    dummy_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    msg2_payload = {
        "msg_id": "m_test_2",
        "sender": "Bob",
        "content": "Here is a view-only photo",
        "image": dummy_base64
    }
    res_msg2 = client.post(f"/api/rooms/{pin}/send", json=msg2_payload)
    assert_test("Bob sends photo with base64 payload", res_msg2.status_code == 200)
    data_msg2 = res_msg2.json()
    assert_test("Photo message type is 'image'", data_msg2.get("message", {}).get("type") == "image")

    # Message 3: Long Multi-line text for auto-alignment
    long_content = "This is a comprehensive test message designed to verify that long paragraphs and multi-line blocks of text automatically align and wrap without breaking bubble limits or overflowing horizontal boundaries on mobile and desktop viewports."
    msg3_payload = {
        "msg_id": "m_test_3",
        "sender": "Alice",
        "content": long_content
    }
    res_msg3 = client.post(f"/api/rooms/{pin}/send", json=msg3_payload)
    assert_test("Alice sends long multi-sentence message", res_msg3.status_code == 200)

    # --- 6. Message History & Delta Polling (since_id) ---
    print("\n--- 6. Testing Message History & Delta Polling (since_id) ---")
    all_msgs_res = client.get(f"/api/rooms/{pin}/messages")
    assert_test("GET /api/rooms/{pin}/messages returns all messages", all_msgs_res.status_code == 200)
    all_msgs = all_msgs_res.json().get("messages", [])
    assert_test("All 3 messages exist in room", len(all_msgs) == 3)

    # Test Delta Polling with since_id
    delta_res1 = client.get(f"/api/rooms/{pin}/messages?since_id=m_test_1")
    delta_msgs1 = delta_res1.json().get("messages", [])
    assert_test("Delta polling with since_id=m_test_1 returns only subsequent 2 messages", len(delta_msgs1) == 2)
    assert_test("Delta messages contain m_test_2 and m_test_3", [m["id"] for m in delta_msgs1] == ["m_test_2", "m_test_3"])

    delta_res3 = client.get(f"/api/rooms/{pin}/messages?since_id=m_test_3")
    delta_msgs3 = delta_res3.json().get("messages", [])
    assert_test("Delta polling with latest ID returns 0 new messages (saving bandwidth)", len(delta_msgs3) == 0)

    # --- 7. Serverless Auto-Recovery (get_or_create) ---
    print("\n--- 7. Testing Serverless Auto-Recovery ---")
    uninitialized_pin = "4829"
    recovery_res = client.get(f"/api/rooms/{uninitialized_pin}/messages")
    assert_test("Uninitialized room auto-recovers without 404", recovery_res.status_code == 200)
    assert_test("Auto-recovered room has valid pin", recovery_res.json().get("pin") == uninitialized_pin)

    # --- 8. WebSocket Connection, Ping/Pong, & Broadcast ---
    print("\n--- 8. Testing WebSocket Lifecycle ---")
    ws_pin = pin
    try:
        with client.websocket_connect(f"/ws/{ws_pin}/Dave") as ws:
            # Receive join broadcast or users update
            initial_msg = ws.receive_json()
            assert_test("WebSocket connects and receives initial event", "type" in initial_msg)

            # Test Keep-alive Heartbeat Ping/Pong
            ws.send_json({"type": "ping"})
            pong_res = ws.receive_json()
            assert_test("WebSocket responds to ping with pong heartbeat", pong_res.get("type") == "pong")

            # Send a chat message over WebSocket
            ws.send_json({
                "msg_id": "m_test_ws",
                "sender": "Dave",
                "content": "Hello over WebSockets!"
            })
            broadcast_msg = ws.receive_json()
            assert_test("WebSocket broadcasts message to room", broadcast_msg.get("content") == "Hello over WebSockets!")
    except Exception as e:
        assert_test("WebSocket lifecycle", False, str(e))

    # --- 9. Host Room Termination (/api/rooms/{pin}/close) ---
    print("\n--- 9. Testing Room Deletion by Host ---")
    close_res = client.post(f"/api/rooms/{pin}/close", json={"sender": "Alice", "content": "Closing room"})
    assert_test("Host successfully deletes room", close_res.status_code == 200 and close_res.json().get("status") == "closed")
    assert_test("Room is removed from manager", manager.get_room(pin) is None)

    # --- Summary ---
    print("\n" + "=" * 70)
    print(f"[+] TEST RESULTS SUMMARY: {passed} / {total} Passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
