#!/usr/bin/python

import asyncio
from signal import SIGINT, SIGTERM

import orjson
from core import SwayIPCConnection
from windows import fullscreen_enable, inactive_windows, signal_all


async def timer(ipc: SwayIPCConnection, seconds: int):
    try:
        while True:
            await asyncio.sleep(seconds)
            await inactive_windows(ipc, duration=1)

    except asyncio.CancelledError:
        return


async def event_listener(
    ipc: SwayIPCConnection, subscriptions: dict[str, dict[str, bool]]
) -> None:
    events = [event for event, change in subscriptions.items() if any(change)]

    try:
        await ipc.subscribe(events)

        while True:
            event, change, response = await ipc.listen()
            if not subscriptions[event][change]:
                continue

            match event:
                case "output":
                    asyncio.create_task(inactive_windows(ipc, duration=10))
                    outputs = await ipc.get_outputs()
                    outputs = [
                        (o["name"], o["active"]) for o in outputs if o.get("name")
                    ]
                    if any(o[1] is True for o in outputs):
                        continue
                    for name, _ in outputs:
                        await ipc.run_command(f"output {name} enable")

                case "binding":
                    match response["binding"].get("command"):
                        case "kill":
                            await inactive_windows(ipc)
                        case "layout toggle tabbed split":
                            # this ought to be a window event
                            await signal_all(ipc)

                case "window":
                    if not await fullscreen_enable(ipc, change):
                        await signal_all(ipc)

                case "workspace":
                    await signal_all(ipc)

    except asyncio.CancelledError:
        return


async def main(settings: dict):
    ipc = SwayIPCConnection()
    await ipc.connect()

    for s in [SIGINT, SIGTERM]:
        loop.add_signal_handler(
            s, lambda: [task.cancel() for task in asyncio.all_tasks()]
        )

    seconds: int = settings["timer_seconds"]
    subscriptions: dict[str, dict[str, bool]] = settings["subscriptions"]

    try:
        tasks = [timer(ipc, seconds), event_listener(ipc, subscriptions)]
        await asyncio.gather(*tasks)
    except asyncio.exceptions.CancelledError:
        await inactive_windows(ipc)
    finally:
        await ipc.close()


if __name__ == "__main__":
    with open("settings.json", "rb") as f:
        settings = orjson.loads(f.read())

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(settings))
    finally:
        loop.close()
