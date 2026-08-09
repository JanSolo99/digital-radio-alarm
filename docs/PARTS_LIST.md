# Parts List

Starting point based on the requirements in the project README. Quantities assume one unit built.
No links included here (prices/stock change too fast to hardcode) - happy to search for current
listings once you're ready to buy.

## Compute
- **Raspberry Pi Zero 2 W** - built-in WiFi, small enough for a nightstand.
  - No analog audio jack on this board - see the audio HAT below.
  - Alternative: **Pi 3A+** if you'd rather use a plain headphone-jack amp and skip the I2S HAT. Slightly bigger footprint.
- **microSD card**, 16-32GB, A1/A2 rated (e.g. SanDisk Extreme or similar) - for Raspberry Pi OS Lite.
- **microSD card reader** - if your computer doesn't have one built in, for flashing the OS.

## Audio
- **I2S DAC/amp breakout** - a MAX98357A-based board (e.g. Adafruit's I2S 3W Class D Amp). Takes I2S digital audio straight from the Pi's GPIO and drives a speaker directly - no separate DAC needed.
- **Small speaker**, 3-4Ω, 3W, ~40-45mm - matched to the amp board above.

## Display
- **E-ink display HAT with partial refresh support** - a Waveshare 2.13" or 2.9" e-Paper HAT (SPI). Confirm the specific model/firmware supports partial refresh before buying - not all do, and it matters for a "now playing" bar that updates often.

## Timekeeping
- **DS3231 RTC module** (I2C, coin-cell backed) - keeps time accurate through WiFi/NTP outages. Matters more here than on a typical Pi project because this one's job is waking you up on time.
- **CR2032 coin cell battery** for the RTC module.

## Input
- **EC11 rotary encoder with push-button** - for setting the alarm time and picking a station without a phone.
- **2-3 tactile push buttons** - snooze / dismiss / back, depending on how much you want to load onto the encoder's own click vs. dedicated buttons. (See the "input method" open question in the README - worth finalizing before you commit to an enclosure design.)

## Light
- **Warm-white LEDs** (a few 3mm/5mm LEDs, or a short warm-white LED strip) angled down at the display, old-Kindle-case style.
- **Appropriately sized resistors** for the LEDs' forward voltage/current.
- **Small NPN transistor or logic-level MOSFET** (e.g. 2N2222 or AO3400) if driving more current than a GPIO pin should source directly - lets you PWM-dim the light from software.

## Power
- **Official Raspberry Pi power supply** for whichever Pi model you pick (5V/2.5A micro-USB for Zero 2 W, 5V/3A USB-C for a Pi 4).

## Enclosure & assembly
- **Enclosure** - since this is meant to be "homemade, DIY-designed," this is presumably something you're designing/printing yourself rather than buying off the shelf. Flagging as a to-do rather than a part.
- **Breadboard + jumper wires** for prototyping the circuit before committing to a final layout.
- **Perfboard, wire, solder** for the final soldered assembly.

## Open questions this list depends on
- Final input method (encoder + buttons vs. something else) - affects enclosure cutouts.
- Exact e-ink panel size/model - affects enclosure dimensions and which vendor SDK you'll vendor into `src/display/`.
