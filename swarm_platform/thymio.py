import asyncio

from tdmclient import ClientAsync

from .exceptions import RobotConnectionError
from .utils import ensure_tdm_running


class ThymioConnection:

    def __init__(self):

        self.client = None
        self.client_context = None

        self.node_context = None
        self.node = None

        self.running = False
        self.poll_task = None

    async def connect(self):
        ensure_tdm_running()
        self.client = ClientAsync()
        self.client_context = self.client.__enter__()

        try:
            self.node_context = await self.client.lock()
            self.node = self.node_context.__enter__()
        except Exception as e:
            raise RobotConnectionError(
                "Unable to connect to the Thymio.\n\n"
                "Possible reasons:\n"
                " • No Thymio is connected.\n"
                " • USB permissions are incorrect.\n"
                " • Thymio Device Manager failed to start.\n"
                " • Another program has locked the robot.\n\n"
                f"Original error:\n{e}"
            )

        await self.node.watch(variables=True)

        self.running = True
        self.poll_task = asyncio.create_task(self._poll())

    async def disconnect(self):

        self.running = False

        if self.poll_task:
            await self.poll_task

        if self.node_context:
            self.node_context.__exit__(None, None, None)

        if self.client_context:
            self.client.__exit__(None, None, None)

    async def _poll(self):

        while self.running:

            self.client.process_waiting_messages()

            await asyncio.sleep(0.01)