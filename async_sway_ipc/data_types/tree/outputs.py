from typing import Literal, Never, TypedDict

from data_types.common import Rectangle
from data_types.tree.workspace import RealWorkspace, ScratchWorkspace


class Mode(TypedDict):
    height: int
    picture_aspect_ratio: str
    refresh: int
    width: int


class RealOutput(TypedDict):
    border: str
    current_border_width: int
    deco_rect: Rectangle
    floating_nodes: list[Never]
    focus: list[int]
    focused: bool
    fullscreen_mode: int
    geometry: Rectangle
    id: int
    layout: str
    make: str
    marks: list
    model: str
    modes: list[Mode]
    name: str
    nodes: list[RealWorkspace]
    orientation: str
    percent: int
    primary: bool
    rect: Rectangle
    serial: str
    sticky: bool
    type: Literal["output"]
    urgent: bool
    window: None
    window_rect: Rectangle


class ScratchOutput(TypedDict):
    """
    Holds the single ScratchWorkspace
    """

    border: str
    current_border_width: int
    deco_rect: Rectangle
    floating_nodes: list[Never]
    focus: list[int]
    focused: bool
    fullscreen_mode: int
    geometry: Rectangle
    id: int
    layout: str
    marks: list
    name: Literal["__i3"]
    nodes: list[ScratchWorkspace]
    orientation: str
    percent: None
    rect: Rectangle
    sticky: bool
    type: Literal["output"]
    urgent: bool
    window: None
    window_rect: Rectangle


Output = RealOutput | ScratchOutput
