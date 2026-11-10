"""Deterministic rectangle tatami prototype. Coordinates are in millimeters.

This is the FIRST engine benchmark, not a production digitizer: it intentionally
has no raster segmentation, path clipping, underlay or automatic satin.
"""
from dataclasses import dataclass
from math import ceil, hypot


@dataclass(frozen=True)
class Command:
    kind: str  # STITCH, JUMP, COLOR_CHANGE, END
    x: float
    y: float


def rectangle_tatami(width=35.0, height=18.0, spacing=0.4,
                     stitch_length=2.5, stagger=4):
    """Sew parallel horizontal rows with staggered needle entry positions.

    A JUMP intentionally separates every row. These jumps must not be mistaken
    for sewn coverage. Later milestones will replace them with planned travel.
    """
    if min(width, height, spacing, stitch_length) <= 0 or stagger < 2:
        raise ValueError('Dimensions/spacing/length must be positive; stagger >= 2')
    if width > 300 or height > 300 or spacing < 0.15 or stitch_length < 0.5:
        raise ValueError('Prototype limits: dimensions <= 300mm, spacing >= 0.15mm, stitch length >= 0.5mm')
    rows = max(2, ceil(height / spacing) + 1)
    commands = []
    for row in range(rows):
        y = min(height, row * height / (rows - 1))
        left_to_right = row % 2 == 0
        # Offset the interior points across rows rather than repeating columns.
        offset = (row % stagger) * stitch_length / stagger
        xs = [0.0]
        x = offset if offset > 1e-6 else stitch_length
        while x < width - 1e-6:
            xs.append(x)
            x += stitch_length
        xs.append(width)
        # Avoid tiny (<0.5mm) terminal stitches in this benchmark.
        if len(xs) > 2 and xs[1] - xs[0] < 0.5:
            xs.pop(1)
        if len(xs) > 2 and xs[-1] - xs[-2] < 0.5:
            xs.pop(-2)
        if not left_to_right:
            xs.reverse()
        commands.append(Command('JUMP', xs[0], y))
        commands.extend(Command('STITCH', x, y) for x in xs[1:])
    commands.append(Command('END', commands[-1].x, commands[-1].y))
    return commands


def metrics(commands):
    counts = {kind: sum(c.kind == kind for c in commands)
              for kind in ('STITCH', 'JUMP', 'COLOR_CHANGE', 'END')}
    travel = 0.0
    previous = None
    for cmd in commands:
        if previous is not None and cmd.kind == 'JUMP':
            travel += hypot(cmd.x - previous.x, cmd.y - previous.y)
        if cmd.kind in ('STITCH', 'JUMP'):
            previous = cmd
    counts['jump_distance_mm'] = round(travel, 2)
    return counts
