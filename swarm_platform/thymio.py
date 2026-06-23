from tdmclient import ClientAsync
from .exceptions import ThymioConnectionError, ThymioNotReadyError
from .logger import get_logger


class Thymio:
    def __init__(self):
        self.logger = get_logger("Thymio")
        self.client = None
        self.node = None

    def connect(self):
        """
        Connect to the local Thymio via TDM.
        """
        try:
            self.client = ClientAsync()
            self.node = self.client.awake.wait_for_node()

            if self.node is None:
                raise ThymioNotReadyError("No Thymio node available")

            self.logger.info("Connected to Thymio")

        except Exception as e:
            raise ThymioConnectionError(str(e))

    def _ensure_connected(self):
        if self.node is None:
            raise ThymioConnectionError("Thymio not connected")

    def set_variables(self, vars_dict: dict):
        """
        Low-level variable interface.
        """
        self._ensure_connected()
        return self.node.set_variables(vars_dict)

    def read_variables(self, *names):
        """
        Read variables from Thymio.
        """
        self._ensure_connected()

        result = {}

        for name in names:
            result[name] = self.node[name]

        return result

    def close(self):
        if self.client:
            self.client.close()