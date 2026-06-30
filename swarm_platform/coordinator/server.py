import asyncio
import json
import time

ROBOTS = {}  # robot_id -> {ip, port, last_seen}


HEARTBEAT_TIMEOUT = 30  # seconds


async def handle(reader, writer):
    data = await reader.readline()

    if not data:
        writer.close()
        return

    try:
        msg = json.loads(data.decode())
    except Exception:
        writer.close()
        return

    msg_type = msg.get("type")
    print("[RAW MSG]", msg)

    # -------------------------
    # REGISTER ROBOT
    # -------------------------
    if msg_type == "register":
        ROBOTS[msg["robot_id"]] = {
            "ip": msg["ip"],
            "port": msg["port"],
            "last_seen": time.time()
        }

        print(f"[REGISTER] {msg['robot_id']} -> {msg['ip']}:{msg['port']}")

        writer.write(b'{"type":"ok"}\n')

    # -------------------------
    # HEARTBEAT
    # -------------------------
    elif msg_type == "heartbeat":
        now = time.time()
        print(f"[HEARTBEAT] {msg['robot_id']} delta={now - ROBOTS[msg['robot_id']]['last_seen'] if msg['robot_id'] in ROBOTS else 'NEW'}")

        if msg["robot_id"] in ROBOTS:
            ROBOTS[msg["robot_id"]]["last_seen"] = now

    # -------------------------
    # LIST ROBOTS (laptop uses this)
    # -------------------------
    elif msg_type == "list":
        writer.write(
            (json.dumps({"type": "robots", "robots": ROBOTS}) + "\n").encode()
        )

    else:
        writer.write(b'{"type":"error","msg":"unknown"}\n')

    await writer.drain()
    writer.close()


async def cleanup():
    while True:
        now = time.time()
        to_remove = []

        for rid, r in ROBOTS.items():
            if now - r["last_seen"] > HEARTBEAT_TIMEOUT:
                to_remove.append(rid)

        for rid in to_remove:
            print(f"[REMOVE] {rid} last_seen={now - r['last_seen']:.2f}s ago")
            del ROBOTS[rid]

        await asyncio.sleep(2)


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", 9100)

    print("Swarm Coordinator running on port 9100")

    asyncio.create_task(cleanup())

    async with server:
        await server.serve_forever()


asyncio.run(main())