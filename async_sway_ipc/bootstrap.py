import importlib.util
import os
import sys
from typing import Any, Awaitable, Callable

import orjson
from core import SwayIPCConnection

SubscriptionFunc = Callable[[SwayIPCConnection, dict | list], Awaitable[None]]


def load_function(directory: str, key: str) -> SubscriptionFunc:
    path, funcname = key.split(":")
    path = os.path.join(directory, path) if not os.path.isabs(path) else path
    path += ".py" if not path.endswith(".py") else ""

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Can't load function '{funcname}': {path} does not exist"
        )

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


def ensure_default_dirs_exist(destination: str) -> None:
    dest_dir = os.path.dirname(destination)
    subscription_dir = os.path.join(dest_dir, "subscription_handlers")
    if not os.path.exists(subscription_dir):
        os.makedirs(subscription_dir, exist_ok=True)

    if not os.path.exists(destination):
        ipc_dir = os.path.dirname(__file__)
        template = os.path.join(ipc_dir, "settings.json")
        with open(template, "rb") as src, open(destination, "wb") as dest:
            dest.write(src.read())


def load_funcs_from_settings(
    settings_path: str,
) -> dict[str, dict[str, SubscriptionFunc | None]]:
    with open(settings_path, "rb") as f:
        settings: dict[str, Any] = orjson.loads(f.read())
    subscription_dir = os.path.join(
        os.path.dirname(settings_path), "subscription_handlers"
    )

    func_dict: dict[str, SubscriptionFunc] = {}
    for changes in settings["subscriptions"].values():
        for func_name in changes.values():
            if func_name and func_name not in func_dict:
                func_dict[func_name] = load_function(subscription_dir, func_name)

    return {
        event: {change: func_dict.get(func) for change, func in changes.items()}
        for event, changes in settings["subscriptions"].items()
    }


def initialize_and_load(
    settings_path: str | None = None,
) -> dict[str, dict[str, SubscriptionFunc | None]]:
    if settings_path is None:
        settings_path = os.path.join(
            os.getenv("XDG_CONFIG_HOME", "~/.config"),
            "async-sway-ipc",
            "settings.json",
        )
        settings_path = os.path.expanduser(settings_path)
        ensure_default_dirs_exist(settings_path)
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Path to file does not exist: {settings_path}")

    return load_funcs_from_settings(settings_path)
