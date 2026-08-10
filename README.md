# Digital Radio Alarm

A bedside internet radio alarm clock in a retro wood cabinet. An e-ink display shows the time,
date and a now-playing bar, lit from above by a dimmable warm light. Alarms pair a time with a
station and fade up from silence over about a minute. Everything you'd reach for half-asleep is a
physical knob or button - the phone stays in another room.

**Project site: https://jansolo99.github.io/digital-radio-alarm/**

Status: planning complete, hardware not yet ordered. Station management and alarm scheduling are
built and tested; display, audio, light and input code wait on real hardware.

## Documentation

- [Build plan](https://jansolo99.github.io/digital-radio-alarm/build-plan.html) - the 14-step
  sequence from breadboard to burn-in, with acceptance criteria and review notes
- [Parts list](https://jansolo99.github.io/digital-radio-alarm/parts-list.html) - all 29 items
  with the gotchas worth knowing before ordering
- [Enclosure concepts](https://jansolo99.github.io/digital-radio-alarm/enclosure-concepts.html) -
  the four directions considered, and which one won

## Specification

| | |
|---|---|
| Enclosure | Mitred hardwood, 180×120×100mm, printed bezel and light hood |
| Brain | Raspberry Pi Zero 2 W |
| Display | 1.54" e-ink, 200×200 square, SPI, partial refresh |
| Audio | MAX98357A I2S amp into a 3" 4Ω full-range driver, ported cabinet |
| Controls | EC11 rotary encoder with push-select + 3 tactile buttons |
| Light | 2700K 5V strip, PWM dimmed via MOSFET on GPIO12 or GPIO13 |
| Timekeeping | DS3231 battery-backed RTC on I2C |
| Power | 5V 3A USB, RCM-marked. SELV only - no mains inside the enclosure |

## Design decisions

- **No hosted backend.** Station discovery uses the free, open
  [Radio Browser](https://www.radio-browser.info) database; the stations you actually use live in
  `data/favorites.json` on the Pi. Nothing to host or keep running.
- **Alarms fire entirely on-device** - time and station are stored locally, so waking up never
  depends on a network round-trip.
- **Station search runs server-side, on the Pi.** Radio Browser's API only works through rotating
  mirror hosts discovered via DNS (`all.api.radio-browser.info`), and that DNS step isn't available
  to browser JavaScript. So `src/stations/radio_browser.py` handles lookup, retry and the required
  User-Agent, and `src/web/` serves its own page rather than calling the API from the browser.
- **A DS3231 RTC, despite the Pi not shipping with one.** A Pi restores a stale time at boot and
  only corrects once WiFi and NTP come up. Fine for most projects; not for an alarm clock.
- **The LED dimmer avoids GPIO18/19.** Those are the pins most PWM tutorials pick, and I2S claims
  both for the amplifier. Use GPIO12 or GPIO13.
- **Playback shells out to `mpv`** rather than using a Python audio library - handles the messy
  variety of internet radio stream formats for free.
- **The cabinet is sized around the speaker, not the electronics.** Small-speaker output is mostly
  cone area and enclosure volume. The first spec (50mm driver, ~1L box) had too little of both; a
  3" driver in a ported ~1.1L cabinet is the single biggest thing separating "sounds like a small
  radio" from "sounds good". The 120mm height exists to give the driver frame real clearance.

## Structure

```
src/
  main.py          entry point, wires everything together
  alarm/           scheduling + storage        [built, tested]
  stations/        Radio Browser + favorites   [built, tested]
  web/             local management page       [built, partial]
  audio/           mpv wrapper, volume ramp    [not started]
  display/         e-ink driver + layout       [not started]
  input/           encoder + button handling   [not started]
  light/           PWM front-light control     [not started]
data/
  favorites.json   saved stations
  alarms.json      configured alarms
docs/              the GitHub Pages project site
systemd/
  digitalradioalarm.service       runs the clock app on boot
  digitalradioalarm-web.service   runs the management page on boot
```

`tests/` isn't created yet - it'll show up alongside the first module complex enough to need a
suite rather than the ad-hoc verification used so far.

## Setup

1. Flash Raspberry Pi OS Lite 64-bit with Raspberry Pi Imager, presetting hostname
   `radioclock.local`, WiFi, timezone and SSH.
2. `sudo apt install mpv libmpv-dev` and enable SPI + I2C via `raspi-config`.
3. `pip install -r requirements.txt`
4. Wire up per the [build plan](https://jansolo99.github.io/digital-radio-alarm/build-plan.html)
   step 3, and prove each subsystem on a breadboard before any woodwork.
5. Copy both `systemd/*.service` files to `/etc/systemd/system/`, then
   `sudo systemctl enable --now digitalradioalarm digitalradioalarm-web`.
6. Browse to `http://radioclock.local:8080/` from any device on the same WiFi to search stations
   and manage favorites.

The management page currently binds to all interfaces with no authentication. That's fine behind a
home router, but never port-forward it, and add a token before considering step 6 finished.
