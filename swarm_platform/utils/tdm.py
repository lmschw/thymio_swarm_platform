import socket

from tdmclient import ClientAsync


def _tdm_ready():
    """
    Real readiness check: can tdmclient actually connect?
    """
    try:
        client = ClientAsync()
        client.__enter__()
        client.__exit__(None, None, None)
        return True
    except Exception:
        return False


def ensure_tdm_running(timeout=2):
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