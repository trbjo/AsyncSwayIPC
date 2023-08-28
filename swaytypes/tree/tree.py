from typing import Literal, Never, TypedDict

from swaytypes.common import Rectangle
from swaytypes.tree.outputs import Output


class Tree(TypedDict):
    id: int
    type: Literal["root"]
    orientation: Literal["horizontal"]
    percent: Literal[None]
    urgent: Literal[False]
    marks: list[Never]
    focused: Literal[False]
    layout: Literal["splith"]
    border: Literal["none"]
    current_border_width: Literal[0]
    rect: Rectangle
    deco_rect: Rectangle
    window_rect: Rectangle
    geometry: Rectangle
    name: Literal["root"]
    window: Literal[None]
    nodes: list[Output]
    floating_nodes: list[Never]
    focus: list[int]
    fullscreen_mode: Literal[0]
    sticky: Literal[False]
