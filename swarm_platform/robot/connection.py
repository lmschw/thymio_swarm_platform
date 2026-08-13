import asyncio
from typing import Any, Optional

from tdmclient import ClientAsync

from ..utils.exceptions import RobotConnectionError
from ..utils.tdm import ensure_tdm_running


class ThymioConnection:

    """
    Manages the low-level connection to a Thymio robot via the Thymio
    Device Manager (TDM).

    Handles waiting for and locking a stable Thymio node, enabling
    proximity communication, and polling for incoming messages/events
    for the lifetime of the connection. Can be used as an async context
    manager.
    """

    def __init__(self) -> None:
        """
        Initializes the connection state; does not connect to a node yet.
        """

        self.client: Optional[ClientAsync] = None

        self.node: Optional[Any] = None
        self.node_context: Optional[Any] = None

        self.running: bool = False
        self.poll_task: Optional["asyncio.Task[None]"] = None

    async def _wait_for_ready_node(self, timeout: float = 10) -> Any:
        """
        Waits for a Thymio node to appear and remain stable.

        Repeatedly processes waiting messages and looks at the list of
        known nodes. A node is considered ready once the same node has
        been seen continuously for more than 0.5 seconds.

        Args:
            timeout: Maximum number of seconds to wait for a stable node.

        Returns:
            The stable Thymio node object.

        Raises:
            RobotConnectionError: If no stable node was detected before
                the timeout elapsed.
        """

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
    
    async def connect(self) -> None:
        """
        Connects to a Thymio robot through the Thymio Device Manager.

        Ensures the TDM is running, opens a ``ClientAsync`` connection,
        waits for a stable node, locks it, enables variable/event
        watching and proximity communication (``prox.comm.enable``),
        waits for the first sensor frame to be published, and starts
        the background polling task.

        Raises:
            RobotConnectionError: If no stable node is detected, or if
                compiling/running the ``prox.comm.enable`` call fails.
            RuntimeError: If the Thymio Device Manager is not running
                (raised by ``ensure_tdm_running``).
        """

        ensure_tdm_running()

        self.client = ClientAsync()
        self.client.__enter__()

        print("Waiting for stable node...")

        self.node = await self._wait_for_ready_node()

        print("Node detected:", self.node)

        # ONLY NOW do we lock
        await self.node.lock()

        await self.node.watch(variables=True, events=True)

        # prox.comm.enable is a native VM function, not a variable -- it
        # must be invoked via compiled Aseba code, not set_variables().
        error = await self.node.compile("call prox.comm.enable(1)")
        if error is not None:
            raise RobotConnectionError(
                f"Failed to compile prox.comm.enable: {error}"
            )
        error = await self.node.run()
        if error is not None:
            raise RobotConnectionError(
                f"Failed to run prox.comm.enable: {error}"
            )

        # IMPORTANT: give TDM time to publish first sensor frame
        for _ in range(50):
            self.client.process_waiting_messages()

            if self.node.var.get("prox.horizontal") is not None:
                break

            await asyncio.sleep(0.05) 

        self.running = True
        self.poll_task = asyncio.create_task(self._poll())

    async def disconnect(self) -> None:
        """
        Disconnects from the Thymio robot and releases resources.

        Stops the polling loop and cancels its task, unlocks the node
        (ignoring any errors), and exits the ``ClientAsync`` context
        (ignoring any errors), resetting all connection state.
        """

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

    async def process_messages(self) -> None:
        """
        Processes any messages waiting on the TDM client connection.
        """
        self.client.process_waiting_messages()

    async def _poll(self) -> None:
        """
        Background loop that continuously processes waiting messages.

        Runs until ``self.running`` is set to ``False`` (by
        :meth:`disconnect`), sleeping briefly between each iteration.
        """

        while self.running:

            await self.process_messages()

            await asyncio.sleep(0.01)

    async def __aenter__(self) -> "ThymioConnection":
        """
        Async context manager entry point; connects to the robot.

        Returns:
            This connection instance, once connected.
        """

        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """
        Async context manager exit point; disconnects from the robot.

        Args:
            exc_type: The exception type raised in the ``with`` block, if any.
            exc: The exception instance raised in the ``with`` block, if any.
            tb: The traceback of the exception raised in the ``with`` block, if any.
        """

        await self.disconnect()