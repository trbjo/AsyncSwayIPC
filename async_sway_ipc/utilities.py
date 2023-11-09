from typing import Callable

from data_types.container import ApplicationContainer


async def rec_parse_tree(node: dict | list, func: Callable) -> list:
    if isinstance(node, list):
        return [item for elem in node for item in await rec_parse_tree(elem, func)]

    if (result := await func(node)) is not None:
        return [result]

    return await rec_parse_tree([*node["floating_nodes"], *node["nodes"]], func)


async def app_finder(n: dict) -> ApplicationContainer | None:
    if n.get("pid") is not None:
        return n


async def focused_app(n: dict) -> ApplicationContainer | None:
    if n.get("pid") is not None and n.get("focused") is True:
        return n


async def apps_wrapped_in_ws(n: dict) -> list[ApplicationContainer] | None:
    if n["type"] == "workspace" and n["name"] != "__i3_scratch":
        return await rec_parse_tree(n, app_finder)
