from typing import Never, TypedDict

from data_types.common import Rectangle
from data_types.container import Container


class Workspace(TypedDict):
    id: int
    type: str
    orientation: str
    percent: None
    urgent: bool
    marks: list
    layout: str
    border: str
    current_border_width: int
    rect: Rectangle
    deco_rect: Rectangle
    window_rect: Rectangle
    geometry: Rectangle
    name: str
    window: None
    nodes: list[Never]
    floating_nodes: list[Container]
    focus: list[int]
    fullscreen_mode: int
    sticky: bool
    num: int
    output: str
    representation: str
    focused: bool
    visible: bool
