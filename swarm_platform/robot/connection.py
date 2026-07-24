import asyncio

from tdmclient import ClientAsync

from ..utils.exceptions import RobotConnectionError
from ..utils.tdm import ensure_tdm_running


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

        self.client = ClientAsync(debug=3)
        self.client.__enter__()

        print("Waiting for stable node...")

        self.node = await self._wait_for_ready_node()

        print("Node detected:", self.node)

        # ONLY NOW do we lock
        await self.node.lock()

        await self.node.watch(variables=True, events=True)

        print("NODE TYPE:", type(self.node), flush=True)
        print("NODE DIR:", [x for x in dir(self.node) if "event" in x.lower()], flush=True)

        print("CLIENT DIR:", [x for x in dir(self.client) if "event" in x.lower()], flush=True)

        print("NODE DICT:", getattr(self.node, "__dict__", None), flush=True)

        # IMPORTANT: give TDM time to publish first sensor frame
        for _ in range(50):
            self.client.process_waiting_messages()

            if self.node.var.get("prox.horizontal") is not None:
                break

            await asyncio.sleep(0.05)

        await self.node.set_variables({
            "prox.comm.enable": [1],
        })

        self.client.process_waiting_messages()

        print(
            "comm vars:",
            self.node.var.get("prox.comm.tx"),
            self.node.var.get("prox.comm.rx"),
            self.node.var.get("prox.comm.rx._intensities"),
        )

        await self.node.set_variables({
            "prox.comm.tx": [1],
        })

        print(
            "comm vars:",
            self.node.var.get("prox.comm.tx"),
            self.node.var.get("prox.comm.rx"),
            self.node.var.get("prox.comm.rx._intensities"),
        )
        

        self.running = True
        #self.poll_task = asyncio.create_task(self._poll())

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

    async def process_messages(self):
        self.client.process_waiting_messages()

    async def _poll(self):

        while self.running:

            await self.process_messages()

            await asyncio.sleep(0.01)

    async def __aenter__(self):

        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):

        await self.disconnect()