import asyncio
from signal import SIGCONT, SIGSTOP

from misc import (
    PowerStatus,
    get_power_status,
    send_signal,
    set_systemd_target_from_powerstatus,
)


async def update_for_battery_status(appstate):
    power_status = appstate["power_status"] = await get_power_status()
    await set_systemd_target_from_powerstatus(appstate)
    apps = list(appstate["stopped_apps"])
    no_wakeup = appstate["no_wakeup"]
    no_recursion = appstate["no_recursion"]
    for pid, app_id in apps:
        if app_id not in no_wakeup:
            recurse = app_id in no_recursion
            await send_signal(power_status, pid, app_id, recurse)


async def periodically_pause(appstate):
    sleep = False
    long_interval = appstate["seconds_sleep"]
    short_interval = appstate["seconds_wakeup"]
    power_status = appstate["power_status"]
    no_wakeup = appstate["no_wakeup"]

    try:
        while True:
            sleep = not sleep
            for _ in range(long_interval if sleep else short_interval):
                if power_status != appstate["power_status"]:
                    break
                await asyncio.sleep(1)

            power_status = appstate["power_status"]

            if power_status == PowerStatus.ON_BATTERY and sleep:
                my_sign = SIGSTOP
            else:
                my_sign = SIGCONT

            apps = list(appstate["stopped_apps"])
            no_recursion = appstate["no_recursion"]
            for pid, app_id in apps:
                if app_id not in no_wakeup:
                    recurse = app_id in no_recursion
                    await send_signal(my_sign, pid, app_id, recurse)

    except asyncio.CancelledError:
        apps = list(appstate["stopped_apps"])
        print(f"starting {' '.join(app[1] for app in apps)}")
        for pid, app_id in apps:
            await send_signal(SIGCONT, pid, app_id)
        print("shutting down from periodically_pause")
