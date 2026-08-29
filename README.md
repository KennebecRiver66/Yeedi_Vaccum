
# Yeedi Vacuum Integration
![Version](https://img.shields.io/badge/version-1.1.0-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Custom Home Assistant integration for Yeedi robot vacuums using the Ecovacs cloud API.

## Features

- Start / stop cleaning
- Return to dock
- Vacuum state monitoring
- Basic device control

## Supported Devices

- Yeedi Vac Station (mnx7f4)

## Installation

### HACS
1. Add this repository as a custom repository in HACS
2. Install the integration
3. Restart Home Assistant

### Manual
Copy the `custom_components/yeedi` folder into your Home Assistant config directory.

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Yeedi Vacuum"
4. Enter your Ecovacs account credentials
5. If Ecovacs asks to verify this device, enter the code emailed to your
   account to finish setting up the integration

## Requirements

- Home Assistant 2026.7 or newer
- deebot-client 18.5.1, installed automatically by Home Assistant
- Yeedi device linked to Ecovacs account

Device verification needs deebot-client 18.5.0 or newer, and deebot-client
18.5.x requires `cryptography>=48.0.1`. Home Assistant 2026.6 and older pin an
older `cryptography`, so the dependency cannot be installed there — upgrade
Home Assistant to at least 2026.7 (2026.8 already ships deebot-client 18.5.1
itself).

## Device verification

Ecovacs now requires new clients to be verified before they can log in. The
first time you set up the integration (and whenever Ecovacs asks again), it
emails a one-time code to your Ecovacs account and shows a "Verification code"
step. The verified client ID is stored in the config entry, so it stays valid
across Home Assistant restarts and you should not be asked again.

If the stored login later stops working, Home Assistant starts a
re-authentication flow instead of leaving the integration in an error state.

## Important Notes

- You must migrate your Yeedi device to an Ecovacs account before using this integration.
- After migration, the device will not appear in the Yeedi app but will be controllable via Home Assistant.

## Disclaimer

This integration is based on Ecovacs cloud APIs and is not officially supported by Yeedi.
