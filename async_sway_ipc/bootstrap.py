import importlib.util
import os
import sys
from types import ModuleType
from typing import Any, Awaitable, Callable

import orjson
from core import SwayIPCConnection

SubscriptionFunc = Callable[[SwayIPCConnection, dict | list], Awaitable[None]]


def load_functions(subscription_dir: str, events):
    module_cache = {}
    func_dict: dict[str, SubscriptionFunc] = {}
    for changes in events:
        for func_name in changes.values():
            if func_name and func_name not in func_dict:
                path, funcname = func_name.split(":")
                if not os.path.isabs(path):
                    path = os.path.join(subscription_dir, path)
                path += ".py" if not path.endswith(".py") else ""
                if path not in module_cache:
                    module_cache[path] = find_module(path)
                module = module_cache[path]
                func_dict[func_name] = getattr(module, funcname)
    return func_dict


def find_module(path: str) -> ModuleType:
    try:
        sys.path.append(os.path.dirname(path))
        spec = importlib.util.spec_from_file_location("module.name", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        raise ImportError(f"Failed to load from {path}")
    finally:
        sys.path.pop()


def ensure_default_dirs_exist(destination: str) -> None:
    dest_dir = os.path.dirname(destination)
    subscription_dir = os.path.join(dest_dir, "subscription_handlers")
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

    func_dict: dict[str, SubscriptionFunc] = load_functions(
        subscription_dir, settings["subscriptions"].values()
    )

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
