# Home Assistant diagnostic view

The integration exposes these entities after setup:

- RS485 status
- Received frames
- Received bytes
- Last frame
- Frame logger

## Suggested dashboard card

Add a **Markdown card** to a dashboard and use:

```yaml
type: markdown
title: Tigo TAP Diagnose
content: |
  **RS485:** {{ states('sensor.tigo_tap_local_rs485_status') }}
  **Frames:** {{ states('sensor.tigo_tap_local_received_frames') }}
  **Bytes:** {{ states('sensor.tigo_tap_local_received_bytes') }}

  **Letzter Frame:**
  `{{ states('sensor.tigo_tap_local_last_frame') }}`

  **Downloads:**
  [CSV-Aufzeichnung](/local/tigo_tap_local/frames.csv) · [LOG-Aufzeichnung](/local/tigo_tap_local/frames.log)
```

Entity IDs can differ depending on Home Assistant naming. Use the actual entity IDs shown under **Settings → Devices & services → Tigo TAP Local → Entities**.

## Persistent captures

Every recognized frame is appended to:

- `/config/www/tigo_tap_local/frames.csv`
- `/config/www/tigo_tap_local/frames.log`

They are available from Home Assistant at:

- `/local/tigo_tap_local/frames.csv`
- `/local/tigo_tap_local/frames.log`

The in-memory diagnostic buffer remains limited to 500 frames, while the CSV/LOG capture persists until manually deleted. For long-running installations, file rotation will be added before recommending permanent logging.
