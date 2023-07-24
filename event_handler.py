import asyncio
from signal import SIGCONT, SIGSTOP

from core import SwayIPCConnection
from misc import PowerStatus, signal_handler


async def rec_parse_tree(
    node: dict,
    length: int = -1,
    floating: bool = False,
) -> list[tuple[int, str, bool, bool]]:
    try:
        pid: int = node["pid"]
        app_id: str = node["app_id"]
        _visible: bool = node["visible"]
        inhibit_idle: bool = node["inhibit_idle"]
        visible = _visible or inhibit_idle
        focused: bool = node["focused"]
        fullscreen = length == 1 and focused and not floating
        return [(pid, app_id, visible, fullscreen)]
    except KeyError:
        apps = []
        fnodes = node.get("floating_nodes", [])
        tiling = node.get("nodes", [])
        # when we hit a workspace, we start checking if there are more than
        # one tiling window on it by checking the length of nodes
        if node["type"] == "workspace" or length == 1:
            length = len(tiling) + len(fnodes)
        for child in fnodes:
            apps.extend(await rec_parse_tree(child, length, floating=True))
        for child in tiling:
            apps.extend(await rec_parse_tree(child, length, floating=False))
        return apps


async def rec_tree_to_dict(
    tree: list[tuple[int, str, bool, bool]]
) -> dict[int, tuple[int, str, bool, bool]]:
    """
    list[tuple[pid, app_id, visible, fullscreen]
    -> dict[pid,tuple[pid, app_id, visible, fullscreen]]
    """
    apps = {}
    for t in tree:
        if t[2] is True:
            apps[t[0]] = t
        elif t[2] is False and t[0] not in apps:
            apps[t[0]] = t
    return apps


async def app_overview(connection: SwayIPCConnection) -> dict:
    """
    returns a dict of pids and app values, as well as a full screen indicator
    """
    tree = await connection.get_tree()
    apps: list[tuple[int, str, bool, bool]] = await rec_parse_tree(tree)
    return await rec_tree_to_dict(apps)


async def event_handler(appstate):
    while not (connection := appstate.get("connection")):
        await asyncio.sleep(1)

    try:
        app_dict = await app_overview(connection)

        invisible = []
        for pid, app_id, visible, fullscreen in app_dict.values():
            if fullscreen:
                await connection.run_command(
                    f"[app_id={app_id} con_id=__focused__] fullscreen enable"
                )
            if visible:
                await signal_handler(appstate, pid, app_id, SIGCONT)
            else:
                invisible.append((pid, app_id))

        if appstate["power_status"] != PowerStatus.ON_BATTERY:
            return

        await asyncio.sleep(0.3)

        for pid, app_id in invisible:
            await signal_handler(appstate, pid, app_id, SIGSTOP)

    except asyncio.CancelledError:
        return
