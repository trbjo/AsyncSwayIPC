import asyncio

from core import SwayIPCConnection


async def fullscreen_notify(ipc: SwayIPCConnection, content: dict):
    container: dict = content.get("container")
    action = "Entered" if container.get("fullscreen_mode") == 1 else "Exited"
    message = action + " fullscreen mode"
    app_id: str = container.get("app_id")
    await asyncio.create_subprocess_exec("/usr/bin/notify-send", app_id, message)
