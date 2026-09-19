# tigo-tap-local

Experimental local Tigo TS4 monitoring through a Tigo Access Point (TAP), RS485 and Home Assistant.

> **Current status: passive beta.** Version `0.0.4-beta.2` is designed to capture CCA↔TAP traffic without transmitting. Active CCA replacement/polling is not implemented yet.

## Architecture

```
Tigo TS4 optimizers -> radio -> TAP -> RS485 -> USB-RS485 -> Home Assistant
```

## One-click HACS setup

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alexseuf&repository=tigo-tap-local&category=integration)

If HACS does not accept the redirect, add `https://github.com/alexseuf/tigo-tap-local` manually as a custom repository of category **Integration**. Full instructions: [docs/installation.md](docs/installation.md).

## What the current beta does

- UI setup through **Settings → Devices & services**
- detects `/dev/serial/by-id/*`, `/dev/ttyUSB*` and `/dev/ttyACM*`
- passive receive-only RS485 at 38400 8N1
- extracts observed frames delimited by `7E 07 ... 7E 08`
- keeps the newest 500 frames in memory for diagnostics
- stores one rotating raw capture instead of duplicate CSV + LOG files
- rotation: 10 MiB per file, up to 10 rotated capture files
- Home Assistant button **Diagnosepaket erstellen**
- ZIP export containing `frames.csv`, `frames.log`, `system-info.txt` and raw captures
- generated ZIP: `/local/tigo_tap_local/tigo-tap-diagnostics.zip`

The current parser does **not yet validate checksum/escaping or decode TS4 telemetry**. Captures from this beta are intended to provide the data needed for that next step.

## Installation

See [docs/installation.md](docs/installation.md).

## Hardware

Initial target:
- Tigo TS4 optimizers
- Tigo TAP
- existing CCA during passive capture
- USB-RS485 adapter; galvanic isolation recommended
- Home Assistant host

For the first capture, connect the adapter passively to RS485 A/B while the existing CCA remains the active controller. Do not enable an additional termination resistor unless required by the actual bus topology. See [docs/hardware.md](docs/hardware.md).

## Development roadmap

1. Capture known-good CCA↔TAP traffic.
2. Verify framing, escaping and checksum.
3. Classify CCA requests and TAP responses.
4. Decode TS4 telemetry.
5. Implement safe active polling with the CCA disconnected.
6. Investigate discovery/provisioning and long-term CCA-less operation.

## Protocol research

See [docs/protocol.md](docs/protocol.md) and [docs/research.md](docs/research.md).

## Prior work

Protocol research is informed by the independent projects TapTap, taptap-mqtt and TigoTell. Their licenses must be respected if code is reused.

## Safety

The TAP interface is a half-duplex RS485 field bus. This beta intentionally does not transmit. Do not run two active masters on the bus.

## License

A project license still needs to be selected before substantial original code is published.
