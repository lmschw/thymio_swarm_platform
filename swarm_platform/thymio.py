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

        #
        # Wait until at least one robot has been discovered.
        #

        for _ in range(100):  # 10 seconds

            self.client.process_waiting_messages()

            if len(self.client.nodes) > 0:
                break

            await asyncio.sleep(0.1)

        else:
            raise RobotConnectionError(
                "No Thymio was discovered.\n\n"
                "Check that:\n"
                " • the robot is connected via USB\n"
                " • the robot is switched on\n"
                " • Thymio Device Manager can see it"
            )

        self.node = list(self.client.nodes)[0]

        try:
            await self.node.lock()

        except Exception as e:

            raise RobotConnectionError(
                f"Unable to lock the Thymio:\n{e}"
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