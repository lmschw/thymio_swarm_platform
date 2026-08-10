import asyncio
import io
from pathlib import Path
from typing import Optional, Union

from ..utils.exceptions import CameraError


class Camera:
    """
    Optional Raspberry Pi camera wrapper (picamera2-backed).

    Detection and initialization are best-effort: if no camera module is
    physically attached, or ``picamera2`` isn't installed, ``available``
    stays ``False`` and capture calls raise ``CameraError`` instead of
    blocking robot startup.
    """

    def __init__(self) -> None:
        """Initializes the camera state; does not touch hardware yet."""
        self._picam2 = None
        self.available: bool = False

    async def start(self) -> None:
        """
        Attempts to detect and start the Pi camera.

        Never raises: on any failure (no camera attached, picamera2 not
        installed, etc.) ``available`` is left/set to ``False``.
        """
        try:
            await asyncio.to_thread(self._start_sync)
            self.available = True
        except Exception:
            self._picam2 = None
            self.available = False

    def _start_sync(self) -> None:
        """Synchronously configures and starts the camera (runs in a thread)."""
        from picamera2 import Picamera2  # imported lazily: not installed off-Pi

        picam2 = Picamera2()
        picam2.configure(picam2.create_still_configuration())
        picam2.start()
        self._picam2 = picam2

    async def capture(self, path: Optional[Union[str, Path]] = None) -> bytes:
        """
        Captures a single JPEG-encoded still frame.

        Args:
            path: If given, the captured JPEG bytes are also written to
                this filesystem path.

        Returns:
            The captured frame, JPEG-encoded.

        Raises:
            CameraError: If no camera is available.
        """
        if not self.available or self._picam2 is None:
            raise CameraError("No camera available on this robot")

        data = await asyncio.to_thread(self._capture_sync)

        if path is not None:
            await asyncio.to_thread(Path(path).write_bytes, data)

        return data

    def _capture_sync(self) -> bytes:
        """Synchronously captures a JPEG frame into memory (runs in a thread)."""
        buffer = io.BytesIO()
        self._picam2.capture_file(buffer, format="jpeg")
        return buffer.getvalue()

    async def stop(self) -> None:
        """Stops and releases the camera, if it was started."""
        if self._picam2 is not None:
            await asyncio.to_thread(self._picam2.close)
            self._picam2 = None

        self.available = False
