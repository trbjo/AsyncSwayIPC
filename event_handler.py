import asyncio
from signal import SIGCONT, SIGSTOP

from misc import PowerStatus, send_signal
from swayipc import SwayIPCConnection


async def rec_parse_tree(
    node: list | dict,
    length: int = -1,
    floating: bool = False,
) -> list[tuple[int, str, bool, bool, bool]]:
    apps = []
    if isinstance(node, list):
        for elem in node:
            apps.extend(await rec_parse_tree(elem, len(node)))
        return apps

    elif isinstance(node, dict):
        try:
            pid: int = node["pid"]
            app_id: str = node["app_id"]
            visible: bool = node["visible"]
            inhibit_idle: bool = node["inhibit_idle"]
            focused: bool = node["focused"]
            full_screen = length == 1 and focused and not floating
            return [(pid, app_id, visible, full_screen, inhibit_idle)]
        except KeyError:
            for child in (floating_nodes := node.get("floating_nodes", [])):
                apps.extend(
                    await rec_parse_tree(child, len(floating_nodes), floating=True)
                )
            for child in (tiling := node.get("nodes", [])):
                apps.extend(await rec_parse_tree(child, len(tiling), floating=False))
            return apps

    raise Exception(f"Unhandled instance: {node}")


async def event_handler(
    appstate,
    connection: SwayIPCConnection,
):
    tree = await connection.get_tree()
    await asyncio.sleep(0)
    apps: list[tuple[int, str, bool, bool, bool]] = await rec_parse_tree(tree)
    await asyncio.sleep(0)

    stopped_apps = []
    no_recursion = appstate["no_recursion"]
    power_status = appstate["power_status"]
    for pid, app_id, visible, enable_full_screen, inhibit_idle in apps:
        try:
            await asyncio.sleep(0)
            if (
                not visible
                and not inhibit_idle
                and power_status == PowerStatus.ON_BATTERY
            ):
                stopped_apps.append((pid, app_id))
                recurse = app_id in no_recursion
                await send_signal(SIGSTOP, pid, app_id, recurse)
            else:
                recurse = app_id in no_recursion
                await send_signal(SIGCONT, pid, app_id, recurse)
                if enable_full_screen:
                    await connection.run_command("fullscreen enable")
        except asyncio.CancelledError:
            return

    appstate["stopped_apps"] = stopped_apps
