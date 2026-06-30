import socket

HOST = "0.0.0.0"
PORT = 9000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

print("Listening...")

while True:
    conn, addr = s.accept()
    print("Connection from", addr)
    conn.sendall(b"hello\n")
    conn.close()