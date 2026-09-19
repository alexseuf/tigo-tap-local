# Installation

## HACS custom repository

Until this project is accepted into the HACS default repository list:

1. Open HACS in Home Assistant.
2. Add `https://github.com/alexseuf/tigo-tap-local` as a custom repository.
3. Select category **Integration**.
4. Install **Tigo TAP Local**.
5. Restart Home Assistant.
6. Add the integration under **Settings → Devices & services**.

## Test / prerelease versions

The intended release model is:

- stable versions: normal GitHub releases/tags
- test versions: GitHub prereleases

HACS can expose prerelease versions when the user enables the corresponding prerelease/beta option for the repository. This gives us an update path through Home Assistant/HACS without manually copying files.

Do not use a test release on a production system unless you are prepared to roll back.

## Current status

The HACS package and Home Assistant integration are scaffolding. Installation/update plumbing is being prepared before active RS485 TAP control is enabled.
