import socket

HOST = "thymio-05"   # or the Pi's IP if hostname doesn't work
PORT = 9000

s = socket.create_connection((HOST, PORT), timeout=5)
print(s.recv(1024))
s.close()