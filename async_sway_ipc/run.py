import asyncio
import sys
from signal import SIGINT, SIGTERM

from bootstrap import SubscriptionFunc, initialize_and_load
from core import SwayIPCConnection


async def run_subscription_loop(
    subscriptions: dict[str, dict[str, SubscriptionFunc | None]],
    ipc: SwayIPCConnection | None = None,
):
    """
    Takes a dict of subscriptions corresponding to the valid events and changes, and
    sets up a subscription. Creates the ipc connection if it does not exist.
    """
    if ipc is None:
        ipc = SwayIPCConnection()

    events = [evnt for evnt, changes in subscriptions.items() if any(changes.values())]
    if not events:
        raise ValueError("No functions registered for events")

    try:
        async for event, change, payload in ipc.subscribe(events):
            if (func := subscriptions[event][change]) is not None:
                await func(ipc, payload)
    except asyncio.exceptions.CancelledError:
        await ipc.close()


def run_sway_ipc(subscriptions: dict[str, dict[str, SubscriptionFunc | None]]):
    """
    takes in a dict of subscriptions, adds signal handlers, and runs the main event loop
    """
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(SIGINT, lambda: [t.cancel() for t in asyncio.all_tasks()])
    loop.add_signal_handler(SIGTERM, lambda: [t.cancel() for t in asyncio.all_tasks()])
    try:
        loop.run_until_complete(run_subscription_loop(subscriptions))
    finally:
        loop.close()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python run.py [path-to-settings.json]")
        sys.exit(1)

    settings_path = sys.argv[1] if len(sys.argv) == 2 else None
    subscriptions = initialize_and_load(settings_path)
    run_sway_ipc(subscriptions)
