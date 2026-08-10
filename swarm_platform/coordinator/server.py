import asyncio
import json
import time
from typing import Any, Dict

ROBOTS: Dict[str, Dict[str, Any]] = {}  # robot_id -> {ip, port, last_seen, capabilities}


HEARTBEAT_TIMEOUT = 30  # seconds


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Handle a single incoming TCP connection from a robot or client.

    Reads one newline-terminated JSON message from the connection and
    dispatches it based on its ``type`` field:

    - ``register``: add/update the sender in the global ``ROBOTS`` table.
    - ``heartbeat``: refresh the sender's ``last_seen`` timestamp.
    - ``list``: reply with the current contents of ``ROBOTS``.
    - anything else: reply with an error message.

    The connection is closed after the message is handled (or on
    malformed/empty input).

    Args:
        reader: Stream to read the incoming JSON message from.
        writer: Stream used to write the response and close the connection.

    Returns:
        None
    """
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
            "last_seen": time.time(),
            "capabilities": msg.get("capabilities", {}),
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


async def cleanup() -> None:
    """Periodically evict robots that have stopped sending heartbeats.

    Runs forever as a background task: every 2 seconds it scans
    ``ROBOTS`` and removes any entry whose ``last_seen`` timestamp is
    older than ``HEARTBEAT_TIMEOUT`` seconds.

    Returns:
        None
    """
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


async def main() -> None:
    """Start the swarm coordinator TCP server and run it forever.

    Binds a TCP server to ``0.0.0.0:9100`` that dispatches each
    connection to :func:`handle`, and launches the :func:`cleanup`
    background task to expire stale robot registrations.

    Returns:
        None
    """
    server = await asyncio.start_server(handle, "0.0.0.0", 9100)

    print("Swarm Coordinator running on port 9100")

    asyncio.create_task(cleanup())

    async with server:
        await server.serve_forever()


asyncio.run(main())