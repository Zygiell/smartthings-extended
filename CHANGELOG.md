# Changelog

## 0.2.1

- Added HACS-ready repository structure.
- Added Home Assistant/HACS metadata and local brand icon.
- Fixed oven auto-detection so appliances such as microwaves exposing
  `samsungce.kitchenModeSpecification` are not mistaken for a dual-cavity oven.
- Preserved the v0.2 oven controls and generic `send_command` action.

## 0.2.0

- Added dual-cavity Samsung oven controls.
- Added dynamic mode, temperature and time preparation entities.
- Added Send settings, Start, Pause and Stop buttons per cavity.
- Start checks Smart Control before sending the start command.

## 0.1.0

- Initial generic SmartThings command service using the OAuth client from
  Home Assistant's official SmartThings integration.
