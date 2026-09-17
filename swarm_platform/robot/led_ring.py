import asyncio
from typing import List, Tuple

from ..utils.exceptions import LedRingError


class LedRing:
    """
    Optional AZDelivery 5V RGB LED ring wrapper (WS2812B/Neopixel).

    Driven over the Pi's hardware SPI bus (ring DIN -> GPIO10/MOSI, pin 19)
    rather than PWM (GPIO18), so it only needs the daemon's user to be in
    the ``spi`` group -- no root access, unlike the more common
    rpi_ws281x/PWM approach (which the swarm-daemon can't safely use since
    it runs arbitrary cloned project code as an unprivileged user).

    Detection and initialization are best-effort: if no ring is physically
    attached, SPI isn't enabled, or the neopixel-spi stack isn't installed,
    ``available`` stays ``False`` and color calls raise ``LedRingError``
    instead of blocking robot startup.
    """

    def __init__(self, num_pixels: int = 12, brightness: float = 0.5) -> None:
        """Initializes the ring state; does not touch hardware yet.

        Args:
            num_pixels: Number of LEDs on the ring (12 on the AZDelivery
                5V RGB LED ring these robots use).
            brightness: Overall brightness scale applied to every pixel,
                from 0.0 (off) to 1.0 (full brightness).
        """
        self.num_pixels = num_pixels
        self.brightness = brightness
        self._pixels = None
        self.available: bool = False

    async def start(self) -> None:
        """
        Attempts to detect and initialize the LED ring over SPI.

        Never raises: on any failure (no ring attached, SPI disabled,
        neopixel-spi not installed, etc.) ``available`` is left/set to
        ``False``.
        """
        try:
            await asyncio.to_thread(self._start_sync)
            self.available = True
        except Exception:
            self._pixels = None
            self.available = False

    def _start_sync(self) -> None:
        """Synchronously opens the SPI bus and configures the ring (runs in a thread)."""
        import board  # imported lazily: only installed/usable on a Pi
        import neopixel_spi

        spi = board.SPI()
        self._pixels = neopixel_spi.NeoPixel_SPI(
            spi,
            self.num_pixels,
            pixel_order=neopixel_spi.GRB,
            brightness=self.brightness,
            auto_write=False,
        )

    async def fill(self, r: int, g: int, b: int) -> None:
        """
        Sets every pixel on the ring to the same color.

        Args:
            r: Red channel value (0-255).
            g: Green channel value (0-255).
            b: Blue channel value (0-255).

        Raises:
            LedRingError: If no LED ring is available.
        """
        if not self.available or self._pixels is None:
            raise LedRingError("No LED ring available on this robot")

        await asyncio.to_thread(self._fill_sync, r, g, b)

    def _fill_sync(self, r: int, g: int, b: int) -> None:
        """Synchronously fills and shows the ring (runs in a thread)."""
        self._pixels.fill((int(r), int(g), int(b)))
        self._pixels.show()

    async def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        """
        Sets a single pixel's color and updates the ring.

        Args:
            index: Index of the pixel to set (0-based).
            r: Red channel value (0-255).
            g: Green channel value (0-255).
            b: Blue channel value (0-255).

        Raises:
            LedRingError: If no LED ring is available.
        """
        if not self.available or self._pixels is None:
            raise LedRingError("No LED ring available on this robot")

        await asyncio.to_thread(self._set_pixel_sync, index, r, g, b)

    def _set_pixel_sync(self, index: int, r: int, g: int, b: int) -> None:
        """Synchronously sets one pixel and shows the ring (runs in a thread)."""
        self._pixels[index] = (int(r), int(g), int(b))
        self._pixels.show()

    async def set_pixels(self, colors: List[Tuple[int, int, int]]) -> None:
        """
        Sets all pixel colors at once and updates the ring.

        Args:
            colors: A list of (r, g, b) tuples, one per pixel, in order.

        Raises:
            LedRingError: If no LED ring is available.
        """
        if not self.available or self._pixels is None:
            raise LedRingError("No LED ring available on this robot")

        await asyncio.to_thread(self._set_pixels_sync, colors)

    def _set_pixels_sync(self, colors: List[Tuple[int, int, int]]) -> None:
        """Synchronously sets all pixels and shows the ring (runs in a thread)."""
        for index, (r, g, b) in enumerate(colors):
            self._pixels[index] = (int(r), int(g), int(b))
        self._pixels.show()

    async def off(self) -> None:
        """Turns off every pixel on the ring. A no-op if no ring is available."""
        if not self.available or self._pixels is None:
            return

        await self.fill(0, 0, 0)

    async def stop(self) -> None:
        """Turns off and releases the ring, if it was started."""
        if self._pixels is not None:
            try:
                await asyncio.to_thread(self._fill_sync, 0, 0, 0)
            except Exception:
                pass
            self._pixels = None

        self.available = False
