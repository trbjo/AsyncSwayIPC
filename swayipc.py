import asyncio
from signal import SIGINT, SIGTERM

from bootstrap import initialize_and_load
from core import SwayIPCConnection


async def main():
    subscriptions = initialize_and_load()
    ipc = SwayIPCConnection()
    events = [evnt for evnt, changes in subscriptions.items() if any(changes.values())]

    try:
        async for event, change, payload in ipc.subscribe(events):
            if (func := subscriptions[event][change]) is not None:
                await func(ipc, payload)
    except asyncio.exceptions.CancelledError:
        await ipc.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    loop.add_signal_handler(SIGINT, lambda: [t.cancel() for t in asyncio.all_tasks()])
    loop.add_signal_handler(SIGTERM, lambda: [t.cancel() for t in asyncio.all_tasks()])

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
