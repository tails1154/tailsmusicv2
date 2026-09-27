# Contributing to TailsMusic

Thanks for helping make TailsMusic better. The project targets Raspberry Pi OS and real Bluetooth hardware, so small, focused changes are easier to review and test safely.

## Before you start

- Read `AGENTS.md` for runtime, navigation, and plugin conventions.
- Keep `config.json` local; it is intentionally ignored because button mappings are device-specific.
- Do not commit generated `app.py`, `__pycache__`, local music, or credentials.

## Local checks

Run the same checks as CI:

```bash
uvx ruff check --output-format=github
python3 -m compileall -q player.py tools.py wifi.py hotspot.py portal apps
```

Hardware-dependent behavior should be tested on a Raspberry Pi with a connected Bluetooth device. Mention what hardware and audio stack you used in the pull request.

## App plugins

An app in `apps/` must export:

```python
class APP:
    def __init__(self, dev, queue): ...
    def checkDaemon(self) -> bool: ...
    def start(self): ...
```

Use `exampleApp.py` as the reference implementation and `tools.API` for button and speech helpers.

## Pull requests

Please include:

1. The user-visible behavior that changed.
2. The hardware/runtime environment used for validation.
3. The commands you ran and their results.
4. Any follow-up work that remains.

Keep commits focused and avoid unrelated generated-document changes.
