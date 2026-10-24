"""
Burp Suite Chat Practice Client
Allows sending & receiving messages via HTTP or WebSocket with built-in proxy support for Burp Suite.

Usage:
  # Normal connection:
  python client.py --user Alice

  # Routed through Burp Suite Proxy (127.0.0.1:8080):
  python client.py --user Alice --proxy http://127.0.0.1:8080
"""

import sys
import time
import argparse
import threading
import requests

def run_http_client(username: str, server_url: str, proxy: str = None):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    print(f"\n[+] Started HTTP Chat Client as '{username}'")
    if proxy:
        print(f"[+] Proxy configured: {proxy} (Traffic will show in Burp Suite!)")
    print("[+] Type a message and press Enter. Type 'exit' to quit.\n" + "-"*50)

    last_seen_count = 0

    # Background thread to poll for incoming messages
    def poll_messages():
        nonlocal last_seen_count
        while True:
            try:
                res = requests.get(f"{server_url}/api/messages", proxies=proxies, timeout=5)
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

    # Main thread handles user inputs
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
                "content": user_input
            }
            # Sending HTTP POST request
            resp = requests.post(f"{server_url}/api/send", json=payload, proxies=proxies)
            if resp.status_code != 200:
                print(f"[!] Server returned error: {resp.status_code}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[!] Error sending message: {e}")

def main():
    parser = argparse.ArgumentParser(description="Burp Suite Chat Practice Client")
    parser.add_argument("--user", type=str, default="Alice", help="Your chat username")
    parser.add_argument("--server", type=str, default="http://127.0.0.1:8000", help="Chat server base URL")
    parser.add_argument("--proxy", type=str, default=None, help="Proxy URL, e.g., http://127.0.0.1:8080")

    args = parser.parse_args()
    run_http_client(username=args.user, server_url=args.server, proxy=args.proxy)

if __name__ == "__main__":
    main()
