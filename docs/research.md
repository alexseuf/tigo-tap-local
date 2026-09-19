# Research log

## Objective

Determine the minimum controller behavior required to operate a Tigo TAP locally without a CCA and expose TS4 telemetry to Home Assistant.

## Existing work to study

### TapTap
https://github.com/willglynn/taptap

Primary reference for CCA↔TAP and TS4 protocol reverse engineering.

### TapTap protocol notes
https://github.com/willglynn/taptap/blob/main/docs/protocol.md

Use as the starting point for frame structure, controller/TAP transactions and captured examples.

### taptap-mqtt
https://github.com/litinoveweedle/taptap-mqtt

Useful reference for mapping decoded optimizer data into MQTT/Home Assistant. It should not be confused with a proven CCA replacement.

### TigoTell
https://github.com/gongloo/TigoTell

Useful independent implementation/reference for decoding locally observed Tigo traffic.

## First experiment

The first active experiment should deliberately avoid discovery or configuration.

**Test:** Can an already provisioned TAP be polled by a Linux host after the genuine CCA has been disconnected?

Success criteria:

- TAP responds consistently to valid controller requests.
- Responses contain recognizable TS4 traffic.
- At least optimizer ID and one or more telemetry values can be decoded.
- Operation continues for a meaningful period without CCA intervention.

All TX/RX bytes should be logged with timestamps so failures can be compared against known-good CCA captures.

## Non-goals for milestone 1

- replacing Tigo commissioning tools
- modifying TS4 firmware
- implementing Rapid Shutdown control
- claiming safety-critical equivalence with Tigo hardware
- cloud emulation
