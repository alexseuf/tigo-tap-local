# tigo-tap-local

Open-source interface for local monitoring of Tigo TS4 optimizers through a Tigo Access Point (TAP), RS485, MQTT and Home Assistant.

> **Project status: research / experimental.** The long-term goal is controller-less operation without a Tigo Cloud Connect Advanced (CCA). This is not yet claimed to be a complete CCA replacement.

## Goal

Build a local, cloud-independent monitoring path:

```
Tigo TS4 optimizers
       │  radio
       ▼
      TAP
       │  RS485
       ▼
USB-RS485 adapter
       │
       ▼
Linux / Raspberry Pi
       │
       ├─ TAP protocol service
       └─ MQTT
             │
             ▼
       Home Assistant
```

The first milestone is to communicate with an already provisioned TAP and retrieve TS4 telemetry without the CCA connected. Later milestones may cover discovery/provisioning if the protocol is sufficiently understood.

## Planned telemetry

Depending on TS4 model and protocol support:

- module/input voltage
- output voltage
- current and power
- temperature
- duty cycle
- RSSI / radio quality
- optimizer identifier / serial information
- last-seen and communication diagnostics

## Hardware

Initial development target:

- Tigo TS4 optimizers
- Tigo Access Point (TAP)
- suitable TAP DC power supply
- galvanically isolated USB-RS485 adapter recommended
- Raspberry Pi or other Linux host
- MQTT broker
- Home Assistant

See [docs/hardware.md](docs/hardware.md).

## Protocol

Existing reverse-engineering work indicates that CCA↔TAP communication uses half-duplex RS485. TapTap documents 38400 baud, 8N1 and request/response framing, including receive requests used by the controller to retrieve radio packets buffered by the TAP.

This repository will document observations separately from assumptions. See [docs/protocol.md](docs/protocol.md).

## Home Assistant / HACS

A HACS-compatible Home Assistant custom-integration scaffold is included under `custom_components/tigo_tap_local`.

For installation and the planned stable/test update channel, see [docs/installation.md](docs/installation.md).

**Current limitation:** the integration is installable scaffolding; active CCA-less TAP polling is not implemented yet. Test releases must therefore be treated as experimental.

## Development phases

1. Document hardware and protocol.
2. Capture known-good CCA↔TAP traffic.
3. Implement passive frame decoding.
4. Implement safe active polling against an already provisioned TAP.
5. Decode TS4 telemetry and publish it via MQTT.
6. Add Home Assistant MQTT Discovery.
7. Test long-term operation without CCA.
8. Investigate discovery/provisioning and additional controller functions.

## Safety

The TAP RS485 interface is a field bus. Active transmission can interfere with a connected CCA or other controller. Early development should therefore use passive captures first. Do not connect two active masters unless the bus behavior is understood.

## Prior work / references

This project builds on publicly available reverse-engineering work, especially:

- **TapTap** by Will Glynn: https://github.com/willglynn/taptap
- TapTap protocol documentation: https://github.com/willglynn/taptap/blob/main/docs/protocol.md
- **taptap-mqtt**: https://github.com/litinoveweedle/taptap-mqtt
- **TigoTell**: https://github.com/gongloo/TigoTell

These projects remain independent. Their licenses must be respected if code is reused rather than independently implemented from protocol documentation and observations.

## Contributing

CCA↔TAP captures from different firmware generations and TS4 models are particularly valuable. Before publishing captures, remove unrelated identifiers or network information where appropriate and document hardware/firmware versions when known.

## License

A project license will be selected before substantial original code is published.
