# SolarEx

SolarEx is an experimental, modular web browser experience written in Python and powered by PyQt6.
The project demonstrates a flexible architecture with pluggable render backends, a profile-aware
network stack, and an extensible plugin system.

## Features

- **Modular core** – runtime module loader with dependency registry.
- **Multiple renderers** – pick between the Qt WebEngine powered backend or a lightweight fallback.
- **Profile management** – per-profile cache & storage directories with optional incognito isolation.
- **Plugin framework** – drop plugins inside `solarex/Plugins/` or `~/.config/SolarEx/plugins` and have
  them discovered automatically.
- **Extension support** – inject user scripts listed inside extension manifests.

## Requirements

The application targets Python 3.10+ and depends on the following packages (see `requirements.txt`):

- `PyQt6`
- `PyQt6-WebEngine`
- `httpx`

Install them with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running SolarEx

Launch the browser shell via the main entry script:

```bash
python solarx.py --mode classic --home https://www.google.com/
```

Useful flags:

- `--mode {classic,pov}` – choose between the tabbed classic window or a borderless POV window.
- `--renderer {qtweb,minimal}` – switch render backends. `minimal` uses `QTextBrowser` for environments
  without QtWebEngine support.
- `--incognito` – start with an in-memory profile that avoids writing to disk.
- `--ua` – override the user agent string.

## Development

To quickly validate that the Python sources compile you can run:

```bash
python -m compileall solarex
```

## License

SolarEx is distributed under the terms of the MIT License. See [LICENSE](LICENSE) for details.
