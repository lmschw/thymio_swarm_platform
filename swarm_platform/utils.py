import platform
import shutil
import subprocess
import time

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


def ensure_tdm_running(timeout=20):

    if platform.system() != "Linux":
        return

    # Already usable?
    if _tdm_ready():
        return

    if shutil.which("flatpak") is None:
        raise RuntimeError("Flatpak not installed")

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

        if _tdm_ready():
            print("Thymio Device Manager is ready.")
            return

        time.sleep(0.5)

    raise RuntimeError("TDM did not become ready in time")