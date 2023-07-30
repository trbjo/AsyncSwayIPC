import asyncio
import os
from signal import SIGCONT, SIGSTOP, Signals

# terminal emulators should not be suspended
no_suspend = {"Alacritty", "PopUp", "footclient"}
lock: int = 0
stopped_apps: dict[int, str] = {}


async def signal_wrapper(
    views: list[tuple[int, str]], sign: Signals, lock_sec: float = 0
):
    """
    If lock_sec is set, this method will refuse to
    send SIGSTOP within the time specified
    """
    global lock
    if lock and sign == SIGSTOP:
        return

    if lock_sec > 0 and sign == SIGCONT:
        lock += 1

    for pid, app_id in views:
        send_signal(pid, app_id, sign)

    if not (lock and lock_sec > 0):
        return

    try:
        await asyncio.sleep(lock_sec)
    except asyncio.CancelledError:
        raise asyncio.CancelledError
    finally:
        lock -= 1


def send_signal(parent_pid: int, app_id: str, sign: int):
    """
    Handles starting and stopping of apps.
    """
    if app_id in no_suspend:
        return

    global stopped_apps

    if (sign == SIGCONT and parent_pid not in stopped_apps) or (
        sign == SIGSTOP and parent_pid in stopped_apps
    ):
        return

    if sign == SIGCONT:
        del stopped_apps[parent_pid]
    elif sign == SIGSTOP:
        stopped_apps[parent_pid] = app_id

    # reverse the list because we want to signal children first
    for pid in pid_children(parent_pid)[::-1]:
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


def pid_children(pid: int) -> list[int]:
    # If initial PID does not exist, return an empty list
    if not os.path.exists(f"/proc/{pid}"):
        return []

    pids = [pid]
    for pid in pids:
        try:
            with os.scandir(f"/proc/{pid}/task/") as tasks:
                # For every task directory, try to read the children file.
                children_files = [task.path + "/children" for task in tasks]
        except FileNotFoundError:
            continue

        for child_file in children_files:
            try:
                with open(child_file, "r") as f:
                    child_pids = map(int, f.read().split())
                    # Append any child PID not already in pids list.
                    pids.extend(child for child in child_pids if child not in pids)
            except FileNotFoundError:
                continue

    return pids
