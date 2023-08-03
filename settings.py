import importlib.util
import os
import sys
from typing import Callable

import orjson


def copy_file(source_file, destination_file):
    with open(source_file, "rb") as src:
        with open(destination_file, "wb") as dest:
            dest.write(src.read())


def extract_functions(subscriptions, tasks, modules_dir) -> dict[str, Callable]:
    funcs: set[str] = {
        value
        for subdict in subscriptions.values()
        for value in subdict.values()
        if value
    }
    funcs.update(tasks)
    return {func: load_function(*format_path(modules_dir, func)) for func in funcs}


def load_functions() -> tuple[dict, list]:
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)
    xdg_config: str | None = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config is None:
        raise EnvironmentError("XDG_CONFIG_HOME, is not set, exit")

    settings_dir = f"{xdg_config}/swayipc"
    if not os.path.exists(settings_dir):
        os.mkdir(settings_dir)

    settings_file = f"{settings_dir}/settings.json"
    if not os.path.exists(settings_file):
        copy_file(f"{current_directory}/settings.json", settings_file)
        copy_file(f"{current_directory}/examples.py", f"{settings_dir}/examples.py")

    with open(os.path.abspath(settings_file), "rb") as f:
        settings = orjson.loads(f.read())

    modules_dir = settings.get("module_path", settings_dir)

    subscriptions = settings["subscriptions"]
    tasks = settings["tasks"]

    func_dict = extract_functions(subscriptions, tasks, modules_dir)

    tasks = [func_dict[task] for task in tasks]

    subscriptions = {
        event: {change: func_dict.get(func) for change, func in changes.items()}
        for event, changes in subscriptions.items()
        if any(changes.values())
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
