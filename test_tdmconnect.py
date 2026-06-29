import asyncio
from tdmclient import ClientAsync

async def main():
    client = ClientAsync()
    client.__enter__()

    print("Waiting...")

    node = await client.wait_for_node()

    print(node)
    print(type(node))

    await node.lock()

    print("Locked!")

    await node.unlock()

    client.__exit__(None, None, None)

asyncio.run(main())