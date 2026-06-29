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

    async def _discover_node(self, timeout=10):

        start = asyncio.get_running_loop().time()

        while asyncio.get_running_loop().time() - start < timeout:

            self.client.process_waiting_messages()

            nodes = list(self.client.nodes)

            if nodes:
                return nodes[0]

            await asyncio.sleep(0.1)

        raise RobotConnectionError(
            "No Thymio detected.\n"
            "Check that:\n"
            " • the robot is connected\n"
            " • the robot is powered on\n"
            " • the Device Manager can see it"
        )

    async def connect(self):

        print("1. Ensuring TDM...")
        ensure_tdm_running()

        print("2. Creating client...")
        self.client = ClientAsync()

        print("3. Entering client...")
        self.client.__enter__()

        print("4. Discovering node...")
        await self._discover_node()

        print("5. Locking node...")
        self.node_context = await self.client.lock()

        print("6. Entering node...")
        self.node = self.node_context.__enter__()

        print("7. Watching variables...")
        await self.node.watch(variables=True, events=True)

        print("8. Starting poll task...")
        self.running = True
        self.poll_task = asyncio.create_task(self._poll())

        print("Connected!")

    async def disconnect(self):

        self.running = False

        if self.poll_task is not None:

            self.poll_task.cancel()

            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

            self.poll_task = None

        if self.node_context is not None:

            try:
                self.node_context.__exit__(None, None, None)
            except Exception:
                pass

            self.node_context = None

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