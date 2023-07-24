import glob
import json
import subprocess
from enum import IntEnum
from signal import SIGCONT, SIGSTOP

import psutil


class PowerStatus(IntEnum):
    NOT_A_LAPTOP = 1
    ON_AC = 18
    ON_BATTERY = 19


async def signal_handler(
    appstate: dict,
    pid: int,
    app_id: str,
    sign: PowerStatus | int,
):
    """
    Handles starting and stopping of apps. this is the only method allowed to mutate the
    stopped_apps dict
    """
    stopped_apps: dict[int, str] = appstate["stopped_apps"]
    if sign == SIGCONT:
        try:
            del stopped_apps[pid]
        except KeyError:
            return
    elif sign == SIGSTOP:
        if pid in stopped_apps:
            return
        stopped_apps[pid] = app_id
    else:
        raise ValueError(f"Wrong input argument: {sign}")

    recurse = app_id not in appstate["no_recursion"]

    parent = psutil.Process(pid)

    try:
        parent.send_signal(sign)
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass

    for child in parent.children(recursive=recurse):
        try:
            child.send_signal(sign)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue


async def get_power_status() -> PowerStatus:
    try:
        ac_adapter = next(f for f in glob.glob("/sys/class/power_supply/AC*"))
    except StopIteration:
        return PowerStatus.NOT_A_LAPTOP

    with open(f"{ac_adapter}/online", mode="rb") as fd:
        res = fd.read().decode().split("\x0A")[0]
        if res == "0":
            return PowerStatus.ON_BATTERY
        elif res == "1":
            return PowerStatus.ON_AC
        else:
            raise Exception("Unknown power status")


async def set_systemd_target_from_powerstatus(appstate: dict) -> None:
    match appstate["power_status"]:
        case PowerStatus.ON_AC:
            verb = "stop"
        case PowerStatus.ON_BATTERY:
            verb = "start"
        case _:
            verb = "stop"

    subprocess.Popen(
        ["systemctl", "--user", verb, "battery.target"],
        stdout=subprocess.PIPE,
    ).wait()


async def set_appstate() -> dict:
    with open("settings.json", "r") as f:
        settings = json.load(f)

    appstate = {}
    appstate["stopped_apps"] = {}

    appstate["hibernate"] = set(settings["hibernate"])
    appstate["no_recursion"] = set(settings["no_recursion"])
    appstate["subscriptions"] = {
        "window": settings["window_change"],
        "workspace": settings["workspace_change"],
    }

    appstate["seconds_wakeup"] = settings["seconds_wakeup"]
    appstate["seconds_sleep"] = settings["seconds_sleep"]

    appstate["power_status"] = await get_power_status()
    return appstate
