import importlib.util
import os
import sys
from typing import Any, Awaitable, Callable

import orjson
from core import JSONDict, JSONList, SwayIPCConnection

SubscriptionFunc = Callable[[SwayIPCConnection, JSONDict | JSONList], Awaitable[None]]


def copy_file(src_file: str, dest_file: str) -> None:
    with open(src_file, "rb") as src, open(dest_file, "wb") as dest:
        dest.write(src.read())


def load_function(directory: str, key: str) -> Callable[..., Any]:
    path, funcname = key.split(":")
    path = os.path.join(directory, path) if not os.path.isabs(path) else path
    path += ".py" if not path.endswith(".py") else ""

    if not os.path.isfile(path):
        raise FileNotFoundError(f"File {path} does not exist")

    try:
        sys.path.append(os.path.dirname(path))
        spec = importlib.util.spec_from_file_location("module.name", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, funcname)
        raise ImportError(f"Failed to load {funcname} from {path}")
    finally:
        sys.path.pop()


def setup_environment() -> tuple[str, str]:
    """Sets up the necessary directories and returns the path to the settings file."""
    if not (config := os.environ.get("SWAYIPC")):
        config = f"{os.environ['XDG_CONFIG_HOME']}/swayipc"

    os.makedirs((plugins := os.path.join(config, "plugins")), exist_ok=True)

    s_file = os.path.join(config, "settings.json")
    if not os.path.exists(s_file):
        copy_file(os.path.join(os.path.dirname(__file__), "settings.json"), s_file)
    return s_file, plugins


def load_funcs_from_settings(
    s_file: str, plugins: str
) -> dict[str, dict[str, SubscriptionFunc | None]]:
    with open(s_file, "rb") as f:
        settings: dict[str, Any] = orjson.loads(f.read())

    func_dict: dict[str, SubscriptionFunc] = {}
    for changes in settings["subscriptions"].values():
        for func in changes.values():
            if func:
                func_dict[func] = load_function(plugins, func)

    return {
        event: {change: func_dict.get(func) for change, func in changes.items()}
        for event, changes in settings["subscriptions"].items()
    }


def initialize_and_load() -> dict[str, dict[str, SubscriptionFunc | None]]:
    s_file, plugins = setup_environment()
    return load_funcs_from_settings(s_file, plugins)
