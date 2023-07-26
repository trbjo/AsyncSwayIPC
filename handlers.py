import asyncio
from signal import SIGCONT, SIGSTOP

from core import SwayIPCConnection
from helpers import send_signal, signal_invisible, window_overview


async def window_handler(ipc: SwayIPCConnection):
    try:
        await asyncio.sleep(0.05)

        invisible = []
        for pid, app_id, visible in await window_overview(ipc):
            if visible:
                await send_signal(pid, app_id, SIGCONT)
            else:
                invisible.append((pid, app_id))

        await asyncio.sleep(0.1)

        for pid, app_id in invisible:
            await send_signal(pid, app_id, SIGSTOP)

    except asyncio.CancelledError:
        return


async def output_handler(appstate) -> None:
    try:
        # ipc: SwayIPCConnection = appstate["ipc"]
        # outputs = await ipc.get_outputs()

        await signal_invisible(appstate, sleep=False)

        # give apps a chance to adapt to the new display size
        await asyncio.sleep(2)
        await signal_invisible(appstate, sleep=True)

    except asyncio.CancelledError:
        return
