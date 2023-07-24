import asyncio
from signal import SIGCONT, SIGSTOP

from event_handler import app_overview
from misc import (
    PowerStatus,
    get_power_status,
    set_systemd_target_from_powerstatus,
    signal_handler,
)


async def update_for_battery_status(appstate):
    print("Got SIGUSR signal")
    power_status = appstate["power_status"] = await get_power_status()
    sleep = power_status == PowerStatus.ON_BATTERY
    await set_systemd_target_from_powerstatus(appstate)
    await signal_invisible(appstate, respect_hibernate=False, sleep=sleep)


async def signal_invisible(
    appstate: dict, respect_hibernate: bool, sleep: bool
) -> None:
    while not (connection := appstate.get("connection")):
        await asyncio.sleep(1)
    hibernate = appstate["hibernate"]
    app_dict = await app_overview(connection)
    for pid, app_id, visible, _ in app_dict.values():
        if visible:  # don't disturb visible apps
            continue
        if respect_hibernate and app_id in hibernate:
            continue
        await signal_handler(appstate, pid, app_id, SIGSTOP if sleep else SIGCONT)


async def periodically_pause(appstate):
    try:
        long_interval = appstate["seconds_sleep"]
        short_interval = appstate["seconds_wakeup"]
        power_status = appstate["power_status"]
        sleep = False

        while True:
            if power_status == PowerStatus.ON_BATTERY:
                await signal_invisible(appstate, respect_hibernate=True, sleep=sleep)

            for _ in range(long_interval if sleep else short_interval):
                await asyncio.sleep(1)

            sleep = not sleep

    except asyncio.CancelledError:
        print("shutting down from periodically_pause")
        return
