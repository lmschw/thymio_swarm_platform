import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

msg = {"type": "announce", "id": "test-pi", "port": 9000}

sock.sendto(json.dumps(msg).encode(), ("255.255.255.255", 9999))

print("sent")