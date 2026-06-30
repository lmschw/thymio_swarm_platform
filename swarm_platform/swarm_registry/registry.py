import asyncio
import json
import time

NODES = {}


async def handle(reader, writer):
    data = await reader.readline()

    msg = json.loads(data.decode())

    if msg["type"] == "register":
        NODES[msg["id"]] = {
            "ip": msg["ip"],
            "port": msg["port"],
            "last_seen": time.time()
        }

        print("Registered:", msg["id"], msg["ip"])

    elif msg["type"] == "heartbeat":
        if msg["id"] in NODES:
            NODES[msg["id"]]["last_seen"] = time.time()

    writer.close()


async def cleanup():
    while True:
        now = time.time()
        for k in list(NODES.keys()):
            if now - NODES[k]["last_seen"] > 10:
                del NODES[k]
        await asyncio.sleep(2)


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", 9100)

    asyncio.create_task(cleanup())

    print("Registry listening on 9100")

    async with server:
        await server.serve_forever()


asyncio.run(main())