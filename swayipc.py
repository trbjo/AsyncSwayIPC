#!/usr/bin/python

import asyncio
from signal import SIGCONT, SIGINT, SIGSTOP, SIGTERM

import orjson
from core import SwayIPCConnection
from windows import fullscreen_enable, signal_all, signal_background


async def timer(ipc: SwayIPCConnection, seconds: int):
    try:
        while True:
            await asyncio.sleep(seconds)
            await signal_background(ipc, sign=SIGCONT, seconds=1)

    except asyncio.CancelledError:
        return


async def event_listener(
    ipc: SwayIPCConnection, subscriptions: dict[str, dict[str, bool]]
) -> None:
    events = [event for event, change in subscriptions.items() if any(change)]

    try:
        await ipc.subscribe(events)
        t = asyncio.create_task(signal_background(ipc, sign=SIGSTOP))

        while True:
            event, change, response = await ipc.listen()
            if not subscriptions[event][change]:
                continue

            if event == "output":
                t.cancel()
                t = asyncio.create_task(signal_background(ipc, sign=SIGCONT, seconds=1))
            elif event == "binding":
                command = response["binding"].get("command")
                if command == "kill":
                    await signal_background(ipc, sign=SIGCONT)
                # this ought to be a window event
                elif command == "layout toggle tabbed split":
                    await signal_all(ipc)

            elif (
                event == "window"
                and not await fullscreen_enable(ipc, change)
                or event == "workspace"
            ):
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
        await signal_background(ipc, sign=SIGCONT)
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
