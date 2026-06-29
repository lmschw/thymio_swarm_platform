import platform
import shutil
import socket
import subprocess
import time


TDM_HOST = "127.0.0.1"
TDM_PORT = 8596


def _tdm_available():

    try:
        with socket.create_connection((TDM_HOST, TDM_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def ensure_tdm_running(timeout=15):

    #
    # Windows/macOS:
    # User starts Thymio Suite manually.
    #

    if platform.system() != "Linux":
        return

    #
    # Already running?
    #

    if _tdm_available():
        return

    if shutil.which("flatpak") is None:
        raise RuntimeError(
            "Flatpak not installed."
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
            print("Thymio Device Manager is running.")
            return

        time.sleep(0.25)

    raise RuntimeError(
        "Timed out waiting for the Thymio Device Manager."
    )