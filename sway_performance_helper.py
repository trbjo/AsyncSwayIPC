#!/usr/bin/python3
import asyncio
from asyncio import Task
from signal import SIGINT, SIGTERM, SIGUSR1

from event_handler import event_handler
from misc import set_appstate
from swayipc import get_ipcs
from tasks import periodically_pause, update_for_battery_status


async def main(appstate: dict) -> None:
    subscriptions: dict[str, dict[str, str]] = appstate["subscriptions"]
    subscription_types = [
        sub
        for sub, subdict in subscriptions.items()
        if any(k for k in subdict.values())
    ]

    async with get_ipcs() as connection:
        task = asyncio.create_task(event_handler(appstate, connection))
        await connection.subscribe(subscription_types)

        while True:
            try:
                event, subevent = await connection.listen()
                if not subscriptions[event][subevent]:
                    continue
                task.cancel()
                task = asyncio.create_task(event_handler(appstate, connection))

            except asyncio.CancelledError:
                print("shutting down from main")
                return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    appstate = asyncio.run(set_appstate())
    loop.add_signal_handler(
        SIGUSR1, lambda: asyncio.create_task(update_for_battery_status(appstate))
    )

    pause_task: Task = loop.create_task(periodically_pause(appstate))
    main_task: Task = loop.create_task(main(appstate))

    def shutdown():
        main_task.cancel()
        pause_task.cancel()
        loop.stop()

    for s in [SIGINT, SIGTERM]:
        loop.add_signal_handler(s, shutdown)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(main_task)  # Give the tasks a chance to cleanup
        loop.run_until_complete(pause_task)
        print("Shutdown completed...")
        loop.close()
