# LED ring wiring

Wiring reference for the AZDelivery 5V RGB LED ring (WS2812B, 12 pixels)
handled by [`swarm_platform/robot/led_ring.py`](../swarm_platform/robot/led_ring.py).
The code talks to the ring over the Pi's **hardware SPI0 bus** via
`board.SPI()`, which is fixed to specific pins by the hardware itself — the
wiring below is not a free choice, it's what that call requires.

## Connections

| Ring pin        | Pi physical pin | Pi function      |
|------------------|-----------------|-------------------|
| DIN (data in)    | Pin 19          | GPIO10 / SPI0 MOSI |
| 5V / VCC         | Pin 2 or 4      | 5V                 |
| GND              | Pin 6 (or any GND pin) | GND          |

The ring's `DOUT` pin (if present) is only used to chain a second ring —
leave it unconnected.

**Do not use GPIO18** — that's the pin most Neopixel tutorials show
(PWM/`rpi_ws281x`), but this project deliberately drives the ring over SPI
instead so the daemon never needs root (see the note in
[`add_led_ring_support.sh`](add_led_ring_support.sh)). GPIO18 is not wired to
anything for this setup.

## Diagram

```
   Raspberry Pi                              AZDelivery WS2812B ring
   40-pin header                                  ┌─────────────┐
                                                    │             │
   Pin 2/4  (5V)          ────────────────────────▶│  5V / VCC   │
                                                    │             │
   Pin 6    (GND)         ────────────────────────▶│  GND        │
                                                    │             │
   Pin 19   (GPIO10,      ──[optional 330Ω]────────▶│  DIN        │
             SPI0 MOSI)                            │             │
                                                    │  DOUT       │  (unused —
                                                    └─────────────┘   only for
                                                                       chaining
                                                                       a 2nd ring)
```

Pin numbers above are physical header positions, not GPIO numbers — pin 19
is just where GPIO10 happens to sit on the header.

## Power

At full white and full brightness, 12 WS2812B pixels can draw up to
~720 mA (12 × 60 mA). `LedRing` defaults `brightness=0.5`, roughly halving
that, but the wiring should still be sized for the worst case:

- **One ring, powering from the Pi's 5V pin (pin 2/4):** fine in practice
  with a good Pi power supply (the official 5V/3A ones have headroom for
  this). Simplest option, and what the table above assumes.
- **Multiple rings, or you want headroom for full brightness:** power the
  ring(s) from a separate 5V supply instead, with its ground tied to the
  Pi's GND (common ground) — data still comes from GPIO10 as above.

## Signal integrity (optional but recommended)

These follow the usual Neopixel best practices and matter more as wire
length grows:

- Put a **300-500 Ω resistor** in the DIN line, as close to the ring as
  possible.
- Put a **large capacitor (~1000 µF, 6.3V+)** across the ring's 5V/GND
  right at the ring, to smooth the inrush current.
- Keep the DIN wire short. The Pi's GPIO is 3.3V logic while WS2812B
  expects ~5V logic (`0.7 × Vdd`), so this link is technically out of
  spec — it works reliably in practice for a single short-wired ring
  (especially powered from the same 5V rail, which lowers the effective
  threshold), but if you see flickering/wrong colors, add a logic-level
  shifter (e.g. 74AHCT125) between GPIO10 and DIN.

## Verifying

After wiring, `SPI` needs to be enabled and `/dev/spidev0.0` present —
both handled by [`raspberry_pi_initial_setup.sh`](raspberry_pi_initial_setup.sh)
on a fresh Pi (or [`add_led_ring_support.sh`](add_led_ring_support.sh) as a
retrofit). Run [`verify_led_ring.sh`](verify_led_ring.sh) to confirm the
ring is detected and flash it red/green/blue as an end-to-end check.
