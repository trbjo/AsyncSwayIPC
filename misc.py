import glob
import json
import subprocess
from enum import IntEnum

import psutil


class PowerStatus(IntEnum):
    NOT_A_LAPTOP = 1
    ON_AC = 18
    ON_BATTERY = 19


async def send_signal(sign: int, pid: int, app_id: str = "", recurse: bool = True):
    if app_id == "PopUp":
        return
    parent = psutil.Process(pid)

    try:
        parent.send_signal(sign)
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
    for child in parent.children(recursive=recurse):
        try:
            child.send_signal(sign)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass


async def get_power_status() -> PowerStatus:
    ac_adapter = None
    for f in glob.glob("/sys/class/power_supply/AC*", recursive=False):
        ac_adapter = f
        break
    else:
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
    appstate["no_wakeup"] = set(settings["no_wakeup"])
    appstate["no_recursion"] = set(settings["no_recursion"])
    appstate["subscriptions"] = {
        "window": settings["window_change"],
        "workspace": settings["workspace_change"],
    }
    appstate["stopped_apps"] = []  # pid, app_id

    appstate["seconds_wakeup"] = settings["seconds_wakeup"]
    appstate["seconds_sleep"] = settings["seconds_sleep"]

    appstate["power_status"] = await get_power_status()
    return appstate
