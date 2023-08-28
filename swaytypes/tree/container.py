from typing import Literal, Never, Optional, TypedDict

from swaytypes.common import Rectangle

InhibitReason = (
    Literal["focus"]
    | Literal["fullscreen"]
    | Literal["open"]
    | Literal["none"]
    | Literal["visible"]
)


class IdleInhibitors(TypedDict):
    user: InhibitReason
    application: InhibitReason


class ApplicationContainer(TypedDict):
    id: int
    type: str
    orientation: str
    percent: Optional[float]
    urgent: bool
    marks: list[str]
    focused: bool
    layout: Literal["none"]
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
    focus: list
    fullscreen_mode: int
    sticky: bool
    pid: int
    app_id: str
    visible: bool
    max_render_time: int
    shell: str
    inhibit_idle: bool
    idle_inhibitors: IdleInhibitors


class NodeContainer(TypedDict):
    border: str
    current_border_width: int
    deco_rect: Rectangle
    focus: list[int]
    focused: bool
    fullscreen_mode: int
    geometry: Rectangle
    id: int
    layout: Literal["tabbed"] | Literal["splitv"] | Literal["splith"]
    marks: list
    name: None
    floating_nodes: list[Container]
    nodes: list[Container]
    orientation: str
    percent: float
    rect: Rectangle
    sticky: bool
    type: str
    urgent: bool
    window: None
    window_rect: Rectangle


Container = NodeContainer | ApplicationContainer
