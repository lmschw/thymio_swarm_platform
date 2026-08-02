import socket

from tdmclient import ClientAsync


def _tdm_ready() -> bool:
    """Check whether the Thymio Device Manager is actually usable.

    Real readiness check: can tdmclient actually connect?

    Returns:
        True if a `tdmclient.ClientAsync` connection can be opened and closed
        successfully, False otherwise.
    """
    try:
        client = ClientAsync()
        client.__enter__()
        client.__exit__(None, None, None)
        return True
    except Exception:
        return False


def ensure_tdm_running(timeout: int = 2) -> None:
    """Verify that the Thymio Device Manager's TCP port is accepting connections.

    Args:
        timeout: Maximum time, in seconds, to wait for the connection attempt.

    Raises:
        RuntimeError: If a connection to the Thymio Device Manager on
            127.0.0.1:8596 cannot be established, with instructions on how to
            check/restart the service.
    """
    try:
        with socket.create_connection(("127.0.0.1", 8596), timeout):
            return
    except OSError:
        raise RuntimeError(
            "Thymio Device Manager is not running.\n\n"
            "Try:\n"
            "  sudo systemctl status thymio-device-manager.service\n"
            "  sudo systemctl restart thymio-device-manager.service"
        )