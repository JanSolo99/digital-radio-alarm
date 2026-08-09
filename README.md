# Digital Radio Alarm

A homemade bedside alarm clock built around internet radio streaming: e-ink clock/date display
with a "now playing" bar, small speaker, top-down light for reading the display in the dark, and
an alarm that fades a chosen station up to full volume instead of jumping straight there. Runs on
a Raspberry Pi over WiFi.

Status: early scaffolding - no hardware wired up yet, no playback/display/alarm logic written yet.

## Hardware

See [docs/PARTS_LIST.md](docs/PARTS_LIST.md) for the full list and rationale.

## Design decisions so far

- **No custom backend.** Station discovery uses the free, open [Radio Browser](https://www.radio-browser.info)
  API; stations you actually use are kept in a local favorites file (`data/favorites.json`) on the
  Pi itself. No server to host or maintain.
- **Alarm logic runs entirely on-device** - alarm time + chosen station are stored locally, no
  network round-trip needed to fire an alarm.
- **Stream playback** shells out to `mpv` rather than using a Python audio library directly - simpler
  and handles the wide variety of internet radio stream formats out of the box.
- **Station search uses the Radio Browser API server-side, not from the browser.** Their API only
  works through rotating mirror hosts discovered via DNS (`all.api.radio-browser.info`) - that DNS
  step isn't available to browser JavaScript, so the Pi does the lookup/retry/User-Agent handling
  in Python (`src/stations/radio_browser.py`) and serves its own small local management page
  (`src/web/`) instead of the page talking to Radio Browser directly.

Still open: physical input method (rotary encoder + buttons is the working assumption), and the
exact e-ink panel model (needs to support partial refresh - see parts list).

## Structure

```
src/
  main.py          entry point, wires everything together
  alarm/           alarm scheduling + persistence
  audio/           mpv subprocess wrapper, volume ramp, now-playing metadata
  display/         e-ink driver wrapper + UI layout
  input/           rotary encoder / button handling
  light/           PWM front-light control
  stations/        Radio Browser client + local favorites (read/written by both main.py and web/)
  web/             local management page - search stations, add/remove favorites from your phone
data/
  favorites.json   your saved stations (seeded with one example)
systemd/
  digitalradioalarm.service       run main.py as a service on boot
  digitalradioalarm-web.service   run the management page as a separate service
```

`tests/` isn't created yet - it'll show up alongside the first module that has real logic to test.

## Setup (once hardware is wired up)

1. Flash Raspberry Pi OS Lite to the microSD card, enable WiFi + SSH.
2. `sudo apt install mpv`
3. `pip install -r requirements.txt`
4. Wire up the display/audio HAT/encoder/light per the pinout notes (to be added once the input
   method and exact display model are finalized).
5. Copy both `systemd/*.service` files to `/etc/systemd/system/`, then
   `sudo systemctl enable --now digitalradioalarm digitalradioalarm-web`.
6. Browse to `http://<pi-hostname>.local:5000/` from your phone (same WiFi) to search stations and
   manage favorites.
