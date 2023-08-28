# AsyncSwayIPC: A Fast Asynchronous IPC Library for Sway
## Overview

Sway-IPC is a small, extremely fast, and completely asynchronous IPC library designed specifically for the Sway Wayland compositor. With less than 350 lines of code, this library aims to provide a lean and efficient way to interact with Sway. It is designed to be a high-performance alternative to existing libraries, leveraging the power of python's asyncio and minimizing dependencies.

## Features

- Small Codebase: Excluding the type hints, it's less than 350 lines of code.
- High Performance: Built for speed, utilizing the asynchronous capabilities of Python.
- Minimal Dependencies: The only external dependency is the Orjson library.

## Installation

The package has been submitted for approval in PyPi, so for now you have to download it here.

## Usage

### Low level handling
Those seeking full control can hand roll their own setup with the `SwayIPCConnection` class found in `core.py`.

### For General Use:

Inside settings.json, specify the subscriptions as per your requirements. You can point each event to a Python file and a method within that file.


- Those who just want to "fire and forget" can make use of the more high level functions in `run.py`. You can either pass a settings.

If you prefer a more automated approach, you can utilize run.py, which allows you to specify subscriptions in a settings.json file. This enables a "fire-and-forget" mechanism for handling Sway events.

Create a settings.json file either in your XDG_CONFIG_HOME/async-sway-ipc/ directory or specify its path when running the script.

Inside settings.json, specify the subscriptions as per your requirements. The outer dictionary keys correspond to events and the inner dictionary keys to changes, keeping with the upstream terminology. You can point each event to a Python file and a method within that file.


### For General Use:
If you just need to react to events and react to those, `run.py` which is made for exactly that.

Inside `settings.json`, specify the subscriptions as per your requirements (see `man 7 sway-ipc` for more info). The outer dictionary keys correspond to `events` and the inner dictionary keys to `changes`, keeping with the upstream terminology. You need point each event to a Python file and a method within that file. The syntax for the inner value is `file[.py]:function` where file is either an absolute path or a path inside `subscription_handlers` which is relative to `settings.json`. here is an example for window events:
```json
...
"window": {
    "close": null,
    "floating": null,
    "focus": null,
    "fullscreen_mode": "examples:fullscreen_notify",
    "mark": null,
    "move": null,
    "new": "examples:print_payload",
    "title": null,
    "urgent": null
}
...
```
and the corresponding methods located in examples.py in the directory `substription_handlers`:

```python
import asyncio

from core import SwayIPCConnection
from data_types.container import ApplicationContainer


async def print_payload(ipc: SwayIPCConnection, payload: dict):
    print(payload)


async def fullscreen_notify(ipc: SwayIPCConnection, payload: dict):
    container: ApplicationContainer = payload.get("container")  # pyright: ignore
    action = "Entered" if container["fullscreen_mode"] == 1 else "Exited"
    message = action + " fullscreen mode"
    app_id: str = container["app_id"]
    await asyncio.create_subprocess_exec("/usr/bin/notify-send", app_id, message)
```

All functions must take two arguments as inputs, the first of which will be the ipc, and the second of which will be the payload coming from sway. Having set up these two change handlers for window events will send a desktop notification for fullscreen events, and print the payload to stdout for new windows.

When `run.py` is run without an input argument, it defaults to `~/XDG_CONFIG_HOME/async-sway-ipc`. To specify a different `settings.json`, add its path as an input argument when running the script.

When you have set up your subscriptions, you are ready to run the script:

```bash
python run.py [optional-settings-file.json]
```

### Optional: Running with systemd

For those running the application on a systemd-enabled system, a sample systemd service file is provided in the repository. To use it:

1. Copy the systemd file to `~/.config/systemd/user/`, and name it `async-sway-ipc.service`.
2. Edit the `ExecStart` line in the systemd file to point to your installation location of `run.py`.
3. Enable and start the service.

## Dependencies
- Orjson

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## License

MIT License
