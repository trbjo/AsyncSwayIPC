import asyncio
from signal import SIGCONT, SIGSTOP, Signals

from core import SwayIPCConnection
from send_signal import signal_wrapper


async def rec_parse_tree(node: dict | list) -> list[tuple[int, str, bool]]:
    apps = []

    if isinstance(node, list):
        for elem in node:
            apps.extend(await rec_parse_tree(elem))

        return apps

    try:
        pid: int = node["pid"]
        app_id: str = node["app_id"]
        visible: bool = node["visible"]
        inhibit_idle: bool = node["inhibit_idle"]

        return [(pid, app_id, visible or inhibit_idle)]

    except KeyError:
        apps.extend(await rec_parse_tree(node["floating_nodes"]))
        apps.extend(await rec_parse_tree(node["nodes"]))

        return apps


async def overview(ipc: SwayIPCConnection) -> list[tuple[int, str, bool]]:
    """
    Returns a list of tuples `pid`, `app_id` `active`
    for all windows in Sway
    """
    tree = await ipc.get_tree()
    windows = {}

    for window in await rec_parse_tree(tree):
        pid, app_id, active = window  # pyright: ignore

        # a pid can have multiple windows
        if active is True:
            windows[pid] = window

        elif active is False and pid not in windows:
            windows[pid] = window

    return list(windows.values())


async def fullscreen_enable(ipc: SwayIPCConnection, subevent: str) -> bool:
    if subevent == "fullscreen_mode":
        return False

    for w in await ipc.get_workspaces():
        if (
            w["focused"] is True
            and w["representation"] is not None
            and " " not in w["representation"]
            and not w["floating_nodes"]
        ):
            await ipc.run_command("fullscreen enable")
            return True

    return False


async def inactive_windows(ipc: SwayIPCConnection, duration: float = 0):
    """Sends a Signal to all inactive windows.
    `duration` is a float, if positive it will send SIGCONT, and after the elapsed
    duration send SIGSTOP. If `duration` is negative, it will send SIGSTOP.
    Please note that the function blocks for the duration of `duration`,
    so you might want to wrap this in an asyncio Task
    """
    views = [(pid, app) for pid, app, active in await overview(ipc) if not active]
    if duration > 0:
        await signal_wrapper(views, SIGCONT, duration)
        await inactive_windows(ipc, -1)
    elif duration < 0:
        await signal_wrapper(views, SIGSTOP)
    else:
        await signal_wrapper(views, SIGCONT)


async def signal_all(ipc: SwayIPCConnection):
    fg, bg = [], []
    for pid, app_id, active in await overview(ipc):
        (fg if active else bg).append((pid, app_id))

    await signal_wrapper(fg, SIGCONT)
    await signal_wrapper(bg, SIGSTOP)
