# Installation — Tigo TAP Local

## Current test version

Current integration version: **0.0.4-beta.2**.

This is a passive capture beta. It is intended for collecting CCA↔TAP RS485 traffic. It does not yet replace the CCA and it does not actively poll the TAP.

## Recommended: HACS one-click

1. Open the one-click HACS link from the repository README.
2. Confirm the repository in HACS.
3. Install **Tigo TAP Local**.
4. Restart Home Assistant.
5. Connect the USB-RS485 adapter.
6. Go to **Settings → Devices & services → Add integration**.
7. Search for **Tigo TAP Local**.
8. Select the RS485 port. Prefer `/dev/serial/by-id/...` if available.
9. Keep **38400 baud**.

### Manual HACS fallback

If the one-click redirect is not accepted:

1. Open HACS.
2. Add `https://github.com/alexseuf/tigo-tap-local` as a custom repository.
3. Category: **Integration**.
4. Install **Tigo TAP Local**.
5. Restart Home Assistant.
6. Add the integration under **Settings → Devices & services**.

## First passive capture

For the initial protocol recording, keep the existing CCA connected and active. Connect the USB-RS485 receiver to the same A/B bus in receive-only mode.

After setup, Home Assistant exposes diagnostic entities including RS485 status, received bytes, received frames, last frame and frame logger.

The integration also provides the button **Diagnosepaket erstellen**.

Press it after enough traffic has been captured. The integration creates:

`/config/www/tigo_tap_local/tigo-tap-diagnostics.zip`

Home Assistant serves that file as:

`/local/tigo_tap_local/tigo-tap-diagnostics.zip`

The ZIP contains:
- `frames.csv`
- `frames.log`
- `system-info.txt`
- available `capture.raw*` files

Upload that ZIP for protocol analysis.

## Capture storage

Persistent recording is stored only once as raw capture data. CSV and readable LOG files are generated when the diagnostic ZIP is created.

Rotation limits:
- active capture: 10 MiB
- up to 10 rotated files
- therefore roughly 110 MiB maximum raw capture storage including the active file

The ZIP itself temporarily requires additional storage.

## Updating

When installed through HACS, update the repository through HACS when a newer version is available, then restart Home Assistant if HACS requests it.

## Known beta limitations

- receive-only; no active TAP polling
- frame delimiter detection is preliminary
- checksum and byte escaping are not yet validated
- TS4 telemetry is not yet decoded
- entity IDs are assigned by Home Assistant and may differ from examples/documentation

## Troubleshooting

If no serial port appears:
- verify that Home Assistant can see the USB-RS485 adapter
- unplug/replug it and reopen the integration setup
- prefer `/dev/serial/by-id/...` over `/dev/ttyUSB0` when available

If the integration loads but frame count remains zero:
- verify A/B wiring and polarity
- confirm that CCA↔TAP traffic is present
- make sure the USB-RS485 adapter is not configured to terminate or actively drive the bus

Do not enable active transmission while the CCA is connected.
