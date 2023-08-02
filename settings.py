import importlib.util
import os
import sys
from typing import Callable

import orjson


def load_functions() -> tuple[dict, list]:
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)

    modules_dir: str = os.environ.get("SWAYIPC_MODULES_PATH", current_directory)
    if not os.path.exists(modules_dir):
        raise FileNotFoundError(f"settings file {modules_dir} does not exist")

    settings_file = f"{modules_dir}/settings.json"
    with open(os.path.abspath(settings_file), "rb") as f:
        settings = orjson.loads(f.read())

    tasks = settings["tasks"]

    tasks = [load_function(*format_path(modules_dir, task)) for task in tasks]
    subscriptions = settings["subscriptions"]
    subscriptions = {
        event: {
            change: load_function(*format_path(modules_dir, func)) if func else None
            for change, func in changes.items()
        }
        for event, changes in subscriptions.items()
    }
    return subscriptions, tasks


def format_path(directory: str, key: str) -> tuple[str, str]:
    path, function_name = key.split(":")

    if not path.startswith("/"):
        path = os.path.join(directory, path)

    if not path.endswith(".py"):
        path += ".py"

    if not os.path.exists(path):
        raise FileNotFoundError(f"File {path} does not exist")

    return path, function_name


def load_function(path, function_name) -> Callable:
    original_sys_path = sys.path[:]
    try:
        sys.path.append(os.path.dirname(path))
        spec = importlib.util.spec_from_file_location("module.name", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, function_name, None)
        raise ImportError(f"Failed to load {function_name} from {path}")
    finally:
        sys.path = original_sys_path
