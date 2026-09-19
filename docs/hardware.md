# Hardware

## Target topology

```
TS4 optimizers  ~~ radio ~~>  TAP
                              │
                              │ RS485 A/B
                              ▼
                     isolated USB-RS485
                              │ USB
                              ▼
                     Linux / Raspberry Pi
                              │
                         MQTT broker
                              │
                              ▼
                       Home Assistant
```

## TAP power

When the CCA is removed, the TAP still needs an appropriate DC supply. Verify the exact requirements for the TAP hardware revision being used before wiring it.

Do **not** assume that the USB-RS485 adapter supplies the TAP.

## RS485 adapter

Recommended properties for development:

- galvanic isolation
- Linux support
- automatic TX/RX direction control for half-duplex operation
- stable USB chipset and persistent `/dev/serial/by-id/...` device path

A non-isolated adapter may work on a bench setup, but isolation is preferable for a permanently installed PV system.

## Bus wiring

Use the TAP/CCA installation documentation for A/B polarity, power and termination. Do not infer polarity solely from generic RS485 adapter labels because A/B naming conventions vary among vendors.

## Development setup

For passive captures with a genuine CCA present, the capture interface must not transmit onto the bus. Active controller-emulation tests should be performed with the CCA disconnected.
