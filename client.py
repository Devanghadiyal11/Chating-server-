"""
Burp Suite Chat Practice Client (With Private Rooms Support)
Allows sending & receiving messages via HTTP with built-in proxy support for Burp Suite.

Usage:
  # Join default general room:
  python client.py --user Alice

  # Join or create a private room:
  python client.py --user Alice --room secret-room --password 1234

  # Route through Burp Suite Proxy (127.0.0.1:8080):
  python client.py --user Alice --room secret-room --proxy http://127.0.0.1:8080
"""

import sys
import time
import argparse
import threading
import requests

def run_http_client(username: str, room_id: str, password: str = None, server_url: str = "http://127.0.0.1:8000", proxy: str = None):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    print(f"\n[+] Started HTTP Chat Client as '{username}' in Room '{room_id}'")
    if password:
        print("[+] Room password configured.")
    if proxy:
        print(f"[+] Proxy configured: {proxy} (Traffic will show in Burp Suite!)")
    print("[+] Type a message and press Enter. Type 'exit' to quit.\n" + "-"*50)

    last_seen_count = 0

    # Background thread to poll for incoming messages in this specific room
    def poll_messages():
        nonlocal last_seen_count
        while True:
            try:
                params = {"password": password} if password else {}
                res = requests.get(f"{server_url}/api/rooms/{room_id}/messages", params=params, proxies=proxies, timeout=5)
                if res.status_code == 200:
                    messages = res.json().get("messages", [])
                    if len(messages) > last_seen_count:
                        for msg in messages[last_seen_count:]:
                            sender = msg.get("sender", "Unknown")
                            content = msg.get("content", "")
                            t = msg.get("timestamp", "")
                            if sender != username:
                                print(f"\r[{t}] {sender}: {content}\n> ", end="", flush=True)
                        last_seen_count = len(messages)
            except Exception:
                pass
            time.sleep(1.5)

    poller = threading.Thread(target=poll_messages, daemon=True)
    poller.start()

    # Main loop to send messages
    while True:
        try:
            user_input = input("> ")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break

            payload = {
                "sender": username,
                "content": user_input,
                "password": password
            }
            resp = requests.post(f"{server_url}/api/rooms/{room_id}/send", json=payload, proxies=proxies)
            if resp.status_code != 200:
                print(f"[!] Server returned error: {resp.status_code} {resp.text}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[!] Error sending message: {e}")

def main():
    parser = argparse.ArgumentParser(description="Burp Suite Chat Practice Client")
    parser.add_argument("--user", type=str, default="Alice", help="Your chat username")
    parser.add_argument("--room", type=str, default="general", help="Room ID / Code to join")
    parser.add_argument("--password", type=str, default=None, help="Room password (if protected)")
    parser.add_argument("--server", type=str, default="http://127.0.0.1:8000", help="Chat server base URL")
    parser.add_argument("--proxy", type=str, default=None, help="Proxy URL, e.g., http://127.0.0.1:8080")

    args = parser.parse_args()
    run_http_client(
        username=args.user,
        room_id=args.room,
        password=args.password,
        server_url=args.server,
        proxy=args.proxy
    )

if __name__ == "__main__":
    main()
