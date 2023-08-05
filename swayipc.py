import asyncio
from signal import SIGINT, SIGTERM
from typing import Callable

from core import SwayIPCConnection
from settings import load_functions


async def event_listener(
    ipc: SwayIPCConnection,
    subscriptions: dict[str, dict[str, Callable | None]],
):
    events = list(subscriptions.keys())
    async for event, change, payload in ipc.subscribe(events):
        if func := subscriptions[event][change]:
            await func(ipc, payload)


async def main(loop):
    subscriptions, tasks = load_functions()
    ipc = SwayIPCConnection()

    for s in [SIGINT, SIGTERM]:
        loop.add_signal_handler(
            s, lambda: [task.cancel() for task in asyncio.all_tasks()]
        )

    try:
        aiotasks = [t(ipc) for t in tasks]
        aiotasks.append(event_listener(ipc, subscriptions))
        await asyncio.gather(*aiotasks)
    except asyncio.exceptions.CancelledError:
        await ipc.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(loop))
    finally:
        loop.close()
