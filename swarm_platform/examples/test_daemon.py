import asyncio
import json


async def send(msg, host="10.15.2.63", port=9000):

    reader, writer = await asyncio.open_connection(host, port)

    writer.write((json.dumps(msg) + "\n").encode())
    await writer.drain()

    response = await reader.readline()

    writer.close()
    await writer.wait_closed()

    return json.loads(response.decode())


async def main():

    print("PING:")
    print(await send({"type": "ping"}))

    print("\nSTATUS:")
    print(await send({"type": "status"}))

    print("\nSTART EXPERIMENT:")
    print(await send({
        "type": "start_experiment",
        "name": "obstacle_avoidance",
        "config": {}
    }))


if __name__ == "__main__":
    asyncio.run(main())