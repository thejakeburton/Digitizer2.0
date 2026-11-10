"""Milestone 1: deterministic, millimeter-based rectangle stitch planning.

An inset edge-walk underlay precedes a serpentine, staggered tatami fill.
Stitched row connections remain inside the rectangle; no long diagonal
travel stitches are silently sewn. This is a geometry benchmark, not
production-ready digitizing or a fabric-accurate sew-out simulation.
"""
from dataclasses import dataclass
from math import ceil, hypot, isfinite


@dataclass(frozen=True)
class Command:
    kind: str  # STITCH, JUMP, COLOR_CHANGE, END
    x: float
    y: float


def _line_to(commands, x, y, max_length):
    """Split a sewn move so no stitch exceeds the configured length."""
    prev = commands[-1]
    distance = hypot(x - prev.x, y - prev.y)
    steps = max(1, ceil(distance / max_length))
    for i in range(1, steps + 1):
        t = i / steps
        commands.append(Command('STITCH', prev.x + (x - prev.x) * t,
                                prev.y + (y - prev.y) * t))


def rectangle_tatami(width=35.0, height=18.0, spacing=0.4,
                     stitch_length=2.5, stagger=4, underlay=True):
    """Build an inset edge-walk underlay and continuous serpentine top fill.

    Exactly one initial JUMP is needed without underlay; with underlay
    an additional JUMP repositions from its endpoint to the fill start.
    Rows alternate direction and are joined by short sewn edge moves.
    """
    values = (width, height, spacing, stitch_length)
    if not all(isfinite(v) and v > 0 for v in values) or stagger < 2:
        raise ValueError('Dimensions, spacing and length must be finite and positive; stagger >= 2')
    if width > 300 or height > 300 or spacing < 0.15 or stitch_length < 0.5:
        raise ValueError('Prototype limits: dimensions <= 300mm, spacing >= 0.15mm, stitch length >= 0.5mm')
    if min(width, height) < 1.0:
        raise ValueError('Rectangle needs at least 1mm per side')

    commands = []
    if underlay:
        inset = min(1.2, width / 4, height / 4)
        x0, x1 = inset, width - inset
        y0, y1 = inset, height - inset
        commands.append(Command('JUMP', x0, y0))
        # An inset edge walk is covered by the top fill.
        for x, y in ((x1, y0), (x1, y1), (x0, y1), (x0, y0)):
            _line_to(commands, x, y, stitch_length)

    rows = max(2, ceil(height / spacing) + 1)
    actual_spacing = height / (rows - 1)
    commands.append(Command('JUMP', 0.0, 0.0))
    for row in range(rows):
        y = row * actual_spacing
        offset = (row % stagger) * stitch_length / stagger
        xs = [0.0]
        x = offset if offset > 1e-6 else stitch_length
        while x < width - 1e-6:
            xs.append(x)
            x += stitch_length
        xs.append(width)
        # Avoid tiny interior end stitches while retaining exact row endpoints.
        if len(xs) > 2 and xs[1] - xs[0] < 0.5:
            xs.pop(1)
        if len(xs) > 2 and xs[-1] - xs[-2] < 0.5:
            xs.pop(-2)
        if row % 2:
            xs.reverse()
        if row:
            # Previous row ends on this same edge. This is a short *sewn*
            # vertical connection, never a diagonal jump across the design.
            _line_to(commands, xs[0], y, stitch_length)
        for x in xs[1:]:
            _line_to(commands, x, y, stitch_length)
    commands.append(Command('END', commands[-1].x, commands[-1].y))
    return commands


def metrics(commands):
    counts = {kind: sum(c.kind == kind for c in commands)
              for kind in ('STITCH', 'JUMP', 'COLOR_CHANGE', 'END')}
    jump_distance = stitch_distance = max_stitch = max_jump = 0.0
    previous = None
    for cmd in commands:
        if previous is not None and cmd.kind in ('STITCH', 'JUMP'):
            dist = hypot(cmd.x - previous.x, cmd.y - previous.y)
            if cmd.kind == 'JUMP':
                jump_distance += dist
                max_jump = max(max_jump, dist)
            else:
                stitch_distance += dist
                max_stitch = max(max_stitch, dist)
        if cmd.kind in ('STITCH', 'JUMP'):
            previous = cmd
    counts.update(jump_distance_mm=round(jump_distance, 2),
                  stitch_distance_mm=round(stitch_distance, 2),
                  max_stitch_mm=round(max_stitch, 3),
                  max_jump_mm=round(max_jump, 3))
    return counts
