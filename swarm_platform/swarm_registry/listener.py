import socket
import json
import threading
import time

NODES = {}


def listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 9999))  # listen on all interfaces

    print("Listening for swarm nodes...")

    while True:
        data, addr = sock.recvfrom(1024)

        try:
            msg = json.loads(data.decode())
        except:
            continue

        if msg.get("type") == "announce":
            NODES[msg["id"]] = {
                "ip": addr[0],
                "port": msg["port"],
                "last_seen": time.time()
            }

            print("Registered:", msg["id"], addr[0])


def cleanup():
    while True:
        now = time.time()
        for k in list(NODES.keys()):
            if now - NODES[k]["last_seen"] > 10:
                del NODES[k]
        time.sleep(2)


threading.Thread(target=listen, daemon=True).start()
threading.Thread(target=cleanup, daemon=True).start()

while True:
    time.sleep(1)