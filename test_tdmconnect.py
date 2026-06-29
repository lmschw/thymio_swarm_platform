import asyncio
from tdmclient import ClientAsync

async def main():
    client = ClientAsync(
        zeroconf=False,
        tdm_addr="127.0.0.1",
        tdm_port=8596,
    )

    client.__enter__()

    print("Waiting...")

    node = await client.wait_for_node()

    print(node)

    await node.lock()

    print("Locked!")

    await node.unlock()

    client.__exit__(None, None, None)

asyncio.run(main())