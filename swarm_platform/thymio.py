from tdmclient import ClientAsync

from .exceptions import RobotConnectionError


class ThymioConnection:

    def __init__(self):
        self.client = None
        self.client_context = None
        self.node_context = None
        self.node = None

    async def connect(self):

        self.client = ClientAsync()

        self.client_context = self.client.__enter__()

        try:
            self.node_context = await self.client.lock()
            self.node = self.node_context.__enter__()

        except Exception as e:
            raise RobotConnectionError(e)

        await self.node.watch(variables=True)

    async def disconnect(self):

        if self.node_context is not None:
            self.node_context.__exit__(None, None, None)

        if self.client is not None:
            self.client.__exit__(None, None, None)