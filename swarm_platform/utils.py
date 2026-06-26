import platform
import shutil
import socket
import subprocess
import time


TDM_HOST = "127.0.0.1"
TDM_PORT = 8596


def _tdm_available(host=TDM_HOST, port=TDM_PORT, timeout=0.5):
    """Return True if a Thymio Device Manager is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_tdm_running(timeout=15):
    """
    Ensure a Thymio Device Manager is running.

    On Linux (Raspberry Pi), this will automatically launch the Flatpak
    device manager if necessary.

    On Windows/macOS, this assumes the user has already started
    Thymio Suite.
    """

    # On Windows and macOS, the user normally starts Thymio Suite.
    if platform.system() != "Linux":
        return

    # Already accepting connections?
    if _tdm_available():
        return

    if shutil.which("flatpak") is None:
        raise RuntimeError(
            "Flatpak is not installed, so the Thymio Device Manager "
            "cannot be started automatically."
        )

    print("Starting Thymio Device Manager...")

    subprocess.Popen(
        [
            "flatpak",
            "run",
            "--command=thymio-device-manager",
            "org.mobsya.ThymioSuite",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    start = time.time()

    while time.time() - start < timeout:

        if _tdm_available():
            print("Thymio Device Manager is ready.")
            return

        time.sleep(0.25)

    raise RuntimeError(
        "Timed out waiting for the Thymio Device Manager.\n\n"
        "Try running:\n"
        "    flatpak run --command=thymio-device-manager org.mobsya.ThymioSuite\n"
        "to verify that it starts correctly."
    )