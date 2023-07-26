import glob
import os
from signal import SIGCONT, SIGSTOP

from core import SwayIPCConnection

stopped_apps: dict[int, str] = {}
no_recursion = ["Alacritty", "PopUp"]


async def send_signal(parent_pid: int, app_id: str, sign: int):
    """
    Handles starting and stopping of apps. this is the only method allowed to mutate the
    stopped_apps dict
    """
    global stopped_apps

    if (sign == SIGCONT and parent_pid not in stopped_apps) or (
        sign == SIGSTOP and parent_pid in stopped_apps
    ):
        return

    if sign == SIGCONT:
        del stopped_apps[parent_pid]
    elif sign == SIGSTOP:
        stopped_apps[parent_pid] = app_id

    for pid in pids_for_proc(parent_pid, recursive=app_id not in no_recursion):
        try:
            os.kill(pid, sign)
        except ProcessLookupError:
            stopped_apps.pop(pid, None)
            print(f"Process {app_id}, {pid} does not exist")
            continue
        except PermissionError:
            stopped_apps.pop(pid, None)
            print(f"Not permitted to send signal {sign} to pid {app_id}, {pid}")
            continue


def pids_for_proc(pid: int, recursive: bool = True) -> list[int]:
    pids = [pid]
    idx = 0
    while True:
        pid = pids[idx]
        files = glob.glob(f"/proc/{pid}/task/*/children")
        for file in files:
            try:
                with open(file, "r") as f:
                    file_contents = f.read().split()
            except FileNotFoundError:
                continue
            intlist = set(int(elem) for elem in file_contents)
            for value in intlist:
                if value not in pids:
                    pids.append(value)
        idx += 1

        if not recursive or idx >= len(pids):
            break
    return pids


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


async def window_overview(ipc: SwayIPCConnection) -> list[tuple[int, str, bool]]:
    """
    Returns a list of tuples of (pid, app_id, visibility)
    for all windows in Sway
    """
    tree = await ipc.get_tree()

    windows = {}

    for window in await rec_parse_tree(tree):
        pid, app_id, visible = window  # pyright: ignore

        # a pid can have both visible and invisible windows
        # and we don't want to suspend visible windows
        if visible is True:
            windows[pid] = window

        elif visible is False and pid not in windows:
            windows[pid] = window

    return list(windows.values())


async def signal_invisible(appstate: dict, sleep: bool, all_apps: bool = False):
    ipc: SwayIPCConnection = appstate["ipc"]
    no_wakeup = appstate["no_wakeup"]

    for pid, app_id, visible in await window_overview(ipc):
        if not all_apps and visible and sleep:  # don't put visible apps to sleep
            continue

        if not (all_apps or sleep) and app_id in no_wakeup:
            continue

        await send_signal(pid, app_id, SIGSTOP if sleep else SIGCONT)


async def fullscreen_enable(ipc: SwayIPCConnection, subevent):
    if subevent == "fullscreen_mode" or subevent == "init":
        return

    for w in await ipc.get_workspaces():
        if (
            w["focused"] is True
            and w["representation"] is not None
            and " " not in w["representation"]
            and not w["floating_nodes"]
        ):
            await ipc.run_command("fullscreen enable")
            return
