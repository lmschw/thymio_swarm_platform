import asyncio

from tdmclient import ClientAsync

from .exceptions import RobotConnectionError
from .utils import ensure_tdm_running


class ThymioConnection:

    def __init__(self):

        self.client = None

        self.node = None
        self.node_context = None

        self.running = False
        self.poll_task = None

    async def _wait_for_ready_node(self, timeout=10):

        start = asyncio.get_running_loop().time()

        stable_node = None
        stable_since = None

        while asyncio.get_running_loop().time() - start < timeout:

            self.client.process_waiting_messages()

            nodes = list(self.client.nodes)

            if not nodes:
                stable_node = None
                stable_since = None
                await asyncio.sleep(0.1)
                continue

            node = nodes[0]

            # detect stability (key fix)
            if stable_node != node:
                stable_node = node
                stable_since = asyncio.get_running_loop().time()

            else:
                # node stable for > 0.5s → ready
                if asyncio.get_running_loop().time() - stable_since > 0.5:
                    return node

            await asyncio.sleep(0.1)

        raise RobotConnectionError("No stable Thymio node detected")
    
    async def connect(self):

        ensure_tdm_running()

        self.client = ClientAsync()
        self.client.__enter__()

        print("Waiting for stable node...")

        self.node = await self._wait_for_ready_node()

        print("Node detected:", self.node)

        # ONLY NOW do we lock
        await self.node.lock()

        await self.node.watch(
            variables=True,
            events=True,
        )

        self.running = True
        self.poll_task = asyncio.create_task(self._poll())

    async def disconnect(self):

        self.running = False

        if self.poll_task is not None:

            self.poll_task.cancel()

            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

            self.poll_task = None

        try:
            await self.node.unlock()
        except Exception:
            pass

        if self.client is not None:

            try:
                self.client.__exit__(None, None, None)
            except Exception:
                pass

            self.client = None

        self.node = None

    async def _poll(self):

        while self.running:

            self.client.process_waiting_messages()

            await asyncio.sleep(0.01)

    async def __aenter__(self):

        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):

        await self.disconnect()