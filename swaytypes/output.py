from typing import Literal, Never, TypedDict

from swaytypes.common import Rectangle


class DisabledMode(TypedDict):
    width: int
    height: int
    refresh: int


class DisabledOutput(TypedDict):
    primary: bool
    make: str
    model: str
    serial: str
    modes: list[DisabledMode]
    non_desktop: bool
    type: Literal["output"]
    name: str
    active: Literal[False]
    dpms: Literal[False]
    power: Literal[False]
    current_workspace: Literal[None]
    rect: Rectangle
    percent: Literal[None]


class EnabledMode(TypedDict):
    width: int
    height: int
    refresh: int
    picture_aspect_ratio: str


class EnabledOutput(TypedDict):
    id: int
    type: Literal["output"]
    orientation: str
    percent: float
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
    floating_nodes: list[Never]
    focus: list[int]
    fullscreen_mode: int
    sticky: bool
    primary: bool
    make: str
    model: str
    serial: str
    modes: list[EnabledMode]
    non_desktop: bool
    active: Literal[True]
    dpms: bool
    power: bool
    scale: float
    scale_filter: str
    transform: str
    adaptive_sync_status: str
    current_workspace: str
    current_mode: EnabledMode
    max_render_time: int
    focused: bool
    subpixel_hinting: str


Output = DisabledOutput | EnabledOutput
