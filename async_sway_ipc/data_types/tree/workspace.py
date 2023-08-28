from typing import Literal, TypedDict

from data_types.common import Rectangle
from data_types.container import Container


class ScratchWorkspace(TypedDict):
    border: str
    current_border_width: int
    deco_rect: Rectangle
    floating_nodes: list[Container]
    focus: list[int]
    focused: bool
    fullscreen_mode: int
    geometry: Rectangle
    id: int
    layout: str
    marks: list
    name: Literal["__i3_scratch"]
    nodes: list[Container]
    orientation: str
    percent: None
    rect: Rectangle
    sticky: bool
    type: Literal["workspace"]
    urgent: bool
    window: None
    window_rect: Rectangle


class Workspace(TypedDict):
    border: str
    current_border_width: int
    deco_rect: Rectangle
    floating_nodes: list[Container]
    focus: list[int]
    focused: bool
    fullscreen_mode: int
    geometry: Rectangle
    id: int
    layout: str
    marks: list
    name: str
    nodes: list[Container]
    num: int
    orientation: str
    output: str
    percent: None
    rect: Rectangle
    representation: str
    sticky: bool
    type: Literal["workspace"]
    urgent: bool
    window: None
    window_rect: Rectangle
