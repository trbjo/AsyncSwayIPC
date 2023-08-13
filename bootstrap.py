import importlib.util
import os
import sys
from typing import Any, Awaitable, Callable

import orjson
from core import JSONDict, JSONList, SwayIPCConnection

TaskFunc = Callable[[SwayIPCConnection], Awaitable[None]]
SubscriptionFunc = Callable[[SwayIPCConnection, JSONDict | JSONList], Awaitable[None]]
Subscriptions = dict[str, dict[str, SubscriptionFunc]]
Tasks = list[TaskFunc]

settings_file = "settings.json"
plugins = "plugins"


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


def setup_environment() -> str:
    """Sets up the necessary directories and returns the path to the settings file."""
    if not (config := os.environ.get("SWAYIPC")):
        config = f"{os.environ['XDG_CONFIG_HOME']}/swayipc"

    for dir in {os.path.join(config, name) for name in ["", plugins]}:
        os.makedirs(dir, exist_ok=True)

    s_file = os.path.join(config, settings_file)
    if not os.path.exists(s_file):
        copy_file(os.path.join(os.path.dirname(__file__), settings_file), s_file)
    return s_file


def load_plugins_from_settings(s_file: str) -> tuple[Subscriptions, Tasks]:
    with open(s_file, "rb") as f:
        settings: dict[str, Any] = orjson.loads(f.read())

    funcs: set[str] = set(
        value
        for subdict in settings["subscriptions"].values()
        for value in subdict.values()
        if value
    )

    funcs.update(settings["tasks"])

    plugin_dir = os.path.join(os.path.dirname(s_file), plugins)
    f_dict: dict[str, TaskFunc | SubscriptionFunc] = {
        func: load_function(plugin_dir, func) for func in funcs
    }

    tasks: Tasks = [f_dict[task] for task in settings["tasks"]]  # pyright: ignore
    subs: Subscriptions = {
        event: {change: f_dict.get(func) for change, func in changes.items()}
        for event, changes in settings["subscriptions"].items()
        if any(changes.values())
    }  # pyright: ignore

    return subs, tasks


def initialize_and_load() -> tuple[Subscriptions, Tasks]:
    s_file = setup_environment()
    return load_plugins_from_settings(s_file)
