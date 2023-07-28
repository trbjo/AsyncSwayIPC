import asyncio
import os
from signal import SIGCONT, SIGSTOP

# terminal emulators should not have their grandchildren suspended
no_recursion = {"Alacritty", "PopUp", "foot"}
lock: int = 0
stopped_apps: dict[int, str] = {}


async def signal_wrapper(
    windows: list[tuple[int, str]], sign: int, lock_sec: float = 0
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

    for pid, app_id in windows:
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

    # reverse the list because we want to signal children first
    for pid in pids_for_proc(parent_pid, app_id not in no_recursion)[::-1]:
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


def pids_for_proc(pid: int, recurse: bool) -> list[int]:
    pids = [pid]
    idx = 0
    while True:
        pid = pids[idx]
        with os.scandir(f"/proc/{pid}/task/") as parent_pid:
            for file in parent_pid:
                try:
                    with open(f"{file.path}/children", "r") as f:
                        file_contents = f.read().split()
                except FileNotFoundError:
                    continue

                for value in set(int(child_pid) for child_pid in file_contents):
                    if value not in pids:
                        pids.append(value)
        idx += 1

        if not recurse or idx == len(pids):
            return pids
