# CCA ↔ TAP protocol research

## Purpose

This document tracks what is known about the serial protocol between the Tigo controller/CCA and TAP. It intentionally separates **documented observations** from features that still require verification.

## Physical layer

Based on the TapTap reverse-engineering documentation:

- RS485
- half duplex
- 38400 baud
- 8 data bits
- no parity
- 1 stop bit

For active testing, only one controller/master should transmit unless multi-master behavior has been verified.

## Framing

TapTap documents a framed transport with escaping and integrity checking. Rather than duplicating undocumented assumptions here, the initial implementation should use test vectors derived from known captures and compare encoded/decoded frames byte-for-byte.

Reference:
https://github.com/willglynn/taptap/blob/main/docs/protocol.md

## Important request/response

TapTap documents controller receive requests and TAP receive responses used to retrieve radio packets buffered by the TAP. This is central to the first CCA-less experiment.

Initial hypothesis to test:

1. TAP has previously been provisioned using a genuine CCA/controller.
2. CCA is disconnected.
3. TAP remains powered.
4. Linux host sends only the minimum valid receive/poll request sequence.
5. TAP returns responses containing queued TS4 radio traffic.
6. Decoder extracts TS4 telemetry.

**Do not treat this hypothesis as proven until reproduced and captured.**

## Research questions

- What exact initialization is required after TAP power-up?
- Is a previously provisioned TAP sufficient for normal monitoring without a CCA?
- Which controller packets are mandatory for continuous operation?
- How are sequence counters initialized and advanced?
- Does TAP radio configuration persist across power cycles?
- How often must the controller poll?
- Are there firmware-dependent frame variants?
- Which functions are required for TS4 discovery/provisioning?
- Can all desired telemetry be obtained without cloud services?

## Capture requirements

For every useful capture record:

- CCA model and firmware, if known
- TAP hardware/firmware, if known
- TS4 model(s)
- number of optimizers
- timestamp/timezone
- direction (CCA→TAP or TAP→CCA) where determinable
- serial settings
- whether the capture was passive
- scenario: boot, normal operation, discovery, configuration, etc.

Raw captures should remain unmodified. Decoded/annotated versions should be separate files.

## Implementation principle

Start receive-only. Add transmission only after framing, checksums, escaping and request semantics are verified against known-good traffic.
