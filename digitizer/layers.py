"""Explicit color/layer sequence planner.

The caller supplies objects in sewing order; colors are changed only when the
next object uses different thread. Never group disjoint regions globally by RGB:
doing so could place foreground objects behind background layers.
"""
from dataclasses import dataclass
from .engine import Command
from .shape import polygon_tatami


@dataclass(frozen=True)
class Region:
    color: str
    outer: tuple
    holes: tuple = ()
    role: str = "fill"


def plan_layers(regions, spacing=0.4, stitch_length=2.5):
    """Return (commands, thread_colors) with order preserved.

    The thread_colors list aligns to the first object and each COLOR_CHANGE.
    Each region begins with an explicit jump. No automatic visual ordering yet.
    """
    regions=list(regions)
    if not regions:
        raise ValueError("At least one region is required")
    commands=[]
    colors=[]
    previous_color=None
    for region in regions:
        if region.role != "fill":
            raise ValueError("Only fill regions are supported by this milestone")
        if not isinstance(region.color,str) or len(region.color)!=7 or region.color[0]!="#" or any(c not in "0123456789abcdefABCDEF" for c in region.color[1:]):
            raise ValueError("Use a hex RGB color such as #112233")
        path=polygon_tatami(region.outer,region.holes,spacing=spacing,stitch_length=stitch_length)
        if previous_color != region.color.lower():
            if previous_color is not None:
                commands.append(Command("COLOR_CHANGE",commands[-1].x,commands[-1].y))
            colors.append(region.color.lower())
            previous_color=region.color.lower()
        commands.extend(path[:-1])
    commands.append(Command("END",commands[-1].x,commands[-1].y))
    return commands,colors
