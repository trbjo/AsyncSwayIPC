import asyncio
import glob
import subprocess

from helpers import signal_invisible


def laptop_lid_closed() -> bool:
    with open("/proc/acpi/button/lid/LID/state", mode="r") as fd:
        state = fd.read()
    return "closed" in state


async def on_battery() -> bool:
    try:
        ac_adapter = next(f for f in glob.glob("/sys/class/power_supply/AC*"))
    except StopIteration:
        return False

    with open(f"{ac_adapter}/online", mode="r") as fd:
        return fd.read().strip() == "0"


async def set_systemd_battery_target(on_battery: bool) -> None:
    subprocess.Popen(
        [
            "systemctl",
            "--user",
            "start" if on_battery else "stop",
            "battery.target",
        ],
        stdout=subprocess.PIPE,
    ).wait()


async def update_battery_status(appstate):
    battery = appstate["on_battery"] = await on_battery()
    await set_systemd_battery_target(battery)
    await signal_invisible(appstate, sleep=battery)
