"""Geometry-only polygon tatami planner (millimeters).

Supports one simple polygon with polygonal holes; even/odd scanline intersections.
Top fill is stitched only within each scanline interval. Travel between
intervals is a JUMP unless the straight segment is demonstrably in the shape.
This deliberately prefers extra jumps over accidentally sewing through a hole.
"""
from math import ceil, hypot, isfinite
from .engine import Command, _line_to, metrics


def _validate_ring(ring):
    if len(ring) < 3:
        raise ValueError('A polygon ring requires at least three vertices')
    p = [tuple(map(float, v)) for v in ring]
    if any(len(v) != 2 or not all(isfinite(a) for a in v) for v in p):
        raise ValueError('Coordinates must be finite x/y pairs')
    area2 = sum(x*y2 - x2*y for (x,y),(x2,y2) in zip(p, p[1:]+p[:1]))
    if abs(area2) < 1e-8:
        raise ValueError('Polygon ring has zero area')
    return p



def _intersects(a, b, c, d):
    """Detect intersection, including collinear contact, within tolerance."""
    def orientation(p, q, r):
        z=(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        return 0 if abs(z)<1e-9 else (1 if z>0 else -1)
    def on_segment(p, q, r):
        return (min(p[0],r[0])-1e-9<=q[0]<=max(p[0],r[0])+1e-9 and
                min(p[1],r[1])-1e-9<=q[1]<=max(p[1],r[1])+1e-9)
    o1,o2=orientation(a,b,c),orientation(a,b,d)
    o3,o4=orientation(c,d,a),orientation(c,d,b)
    if o1!=o2 and o3!=o4:
        return True
    return ((o1==0 and on_segment(a,c,b)) or (o2==0 and on_segment(a,d,b)) or
            (o3==0 and on_segment(c,a,d)) or (o4==0 and on_segment(c,b,d)))


def _validate_geometry(outer, holes):
    rings=[outer]+list(holes)
    for ring in rings:
        n=len(ring)
        for i in range(n):
            if hypot(ring[i][0]-ring[(i+1)%n][0],
                     ring[i][1]-ring[(i+1)%n][1])<1e-8:
                raise ValueError('Polygon contains a zero-length edge')
            for j in range(i+1,n):
                if j==i+1 or (i==0 and j==n-1):
                    continue
                if _intersects(ring[i],ring[(i+1)%n],
                               ring[j],ring[(j+1)%n]):
                    raise ValueError('Polygon contains crossing or touching edges')
    for i,hole in enumerate(holes):
        if not all(point_inside(v,outer) for v in hole):
            raise ValueError('Hole extends outside the outer polygon')
        for other in [outer]+holes[:i]:
            for a,b in zip(hole,hole[1:]+hole[:1]):
                for c,d in zip(other,other[1:]+other[:1]):
                    if _intersects(a,b,c,d):
                        raise ValueError('Hole overlaps or touches another boundary')
        if any(point_inside(v,hole) for other_hole in holes[:i] for v in other_hole):
            raise ValueError('Nested holes are not supported')
        if any(point_inside(v,other_hole) for other_hole in holes[:i] for v in hole):
            raise ValueError('Nested holes are not supported')


def point_inside(point, outer, holes=()):
    """Even/odd point-in-polygon, boundary treated as permitted.

    Boundary allowance is for geometric planning only and is NOT pull compensation.
    """
    x,y = point
    def belongs(ring):
        inside = False
        for (x1,y1),(x2,y2) in zip(ring, ring[1:]+ring[:1]):
            cross = (x-x1)*(y2-y1)-(y-y1)*(x2-x1)
            if abs(cross) < 1e-8 and min(x1,x2)-1e-8 <= x <= max(x1,x2)+1e-8 and min(y1,y2)-1e-8 <= y <= max(y1,y2)+1e-8:
                return True, True
            if (y1 > y) != (y2 > y):
                ix = x1 + (y-y1)*(x2-x1)/(y2-y1)
                if ix > x:
                    inside = not inside
        return inside, False
    valid, boundary = belongs(outer)
    if not valid:
        return False
    for hole in holes:
        hit, on_boundary = belongs(hole)
        if hit and not on_boundary:
            return False
    return True


def scanline_intervals(y, outer, holes=(), edge_inset=0.0):
    """Return safe horizontal intervals for an even/odd polygon with holes.

    Scanline intersection uses a half-open edge rule to avoid vertex double-count.
    The inset is horizontal only, NOT a fabric-specific pull compensation.
    """
    def cuts(ring):
        intersections=[]
        for (x1,y1),(x2,y2) in zip(ring, ring[1:]+ring[:1]):
            if (y1 <= y < y2) or (y2 <= y < y1):
                intersections.append(x1+(y-y1)*(x2-x1)/(y2-y1))
        return sorted(intersections)
    xs=cuts(outer)
    if len(xs)%2:
        raise ValueError('Odd boundary intersections: invalid outer polygon')
    intervals=[(a,b) for a,b in zip(xs[::2],xs[1::2]) if b-a>1e-8]
    for hole in holes:
        cuts_h=cuts(hole)
        if len(cuts_h)%2:
            raise ValueError('Odd hole intersections')
        for h0,h1 in zip(cuts_h[::2],cuts_h[1::2]):
            next_intervals=[]
            for a,b in intervals:
                if h1 <= a or h0 >= b:
                    next_intervals.append((a,b))
                else:
                    if h0>a: next_intervals.append((a,min(b,h0)))
                    if h1<b: next_intervals.append((max(a,h1),b))
            intervals=next_intervals
    return [(a+edge_inset,b-edge_inset) for a,b in intervals if b-a>2*edge_inset+1e-8]


def _safe_segment(start, end, outer, holes, step=0.15):
    d=hypot(end[0]-start[0],end[1]-start[1])
    for i in range(ceil(d/step)+1):
        t=i/max(1,ceil(d/step))
        if not point_inside((start[0]+t*(end[0]-start[0]),
                             start[1]+t*(end[1]-start[1])),outer,holes):
            return False
    return True


def polygon_tatami(outer, holes=(), spacing=0.4, stitch_length=2.5,
                   stagger=4, edge_inset=0.0):
    """Plan a horizontal tatami clipped to a polygon, with safe jumps.

    Requires simple, non-self-intersecting rings and holes fully inside outer.
    Geometric checks are sample-based and do not prove fabric coverage.
    """
    outer=_validate_ring(outer)
    holes=[_validate_ring(h) for h in holes]
    _validate_geometry(outer, holes)
    if not all(isfinite(v) and v >= 0 for v in (edge_inset,)) or not (
        isfinite(spacing) and spacing>=0.15 and
        isfinite(stitch_length) and stitch_length>=0.5 and
        isinstance(stagger,int) and stagger>=2):
        raise ValueError('Invalid stitch spacing, length, stagger or inset')
    xs=[p[0] for p in outer]; ys=[p[1] for p in outer]
    height=max(ys)-min(ys)
    if height<0.3 or max(xs)-min(xs)>300 or height>300:
        raise ValueError('Polygon bounds must fit prototype limits')
    rows=max(2,ceil(height/spacing)+1)
    dy=height/rows
    # Build scanline intervals first. When a hole splits several consecutive
    # rows, sewing each lane vertically avoids jumping over the hole on every
    # horizontal row. Changes in interval count create new planning bands.
    scanlines=[]
    for row in range(rows):
        y=min(ys)+(row+0.5)*dy
        intervals=scanline_intervals(y,outer,holes,edge_inset=edge_inset)
        if intervals:
            scanlines.append((row,y,intervals))
    cmds=[]

    def sew_interval(row,y,a,b,reverse):
        if reverse:
            a,b=b,a
        if not cmds or not _safe_segment(
                (cmds[-1].x,cmds[-1].y),(a,y),outer,holes):
            cmds.append(Command('JUMP',a,y))
        else:
            _line_to(cmds,a,y,stitch_length)
        width=abs(b-a)
        offset=(row%stagger)*stitch_length/stagger
        points=[0.0]
        first=offset if offset>1e-8 else stitch_length
        d=first
        while d<width-1e-8:
            points.append(d)
            d+=stitch_length
        points.append(width)
        if len(points)>2 and points[1]<0.5:
            points.pop(1)
        if len(points)>2 and width-points[-2]<0.5:
            points.pop(-2)
        direction=1 if b>a else -1
        for distance in points[1:]:
            _line_to(cmds,a+direction*distance,y,stitch_length)

    # Split the image into maximal consecutive bands with the same number
    # of horizontal intervals. Within each band, sew each interval column
    # across its rows before moving to the next column.
    bands=[]
    for item in scanlines:
        if (not bands or len(item[2])!=len(bands[-1][-1][2])
                or item[0]!=bands[-1][-1][0]+1):
            bands.append([])
        bands[-1].append(item)
    for band in bands:
        count=len(band[0][2])
        for lane in range(count):
            # Opposite vertical directions between lanes reduce repositioning.
            track=band if lane%2==0 else list(reversed(band))
            for i,(row,y,intervals) in enumerate(track):
                a,b=intervals[lane]
                sew_interval(row,y,a,b,reverse=bool(i%2))
    if not cmds:
        raise ValueError('Shape has no fillable scanline intervals')
    cmds.append(Command('END',cmds[-1].x,cmds[-1].y))
    return cmds


def coverage_report(commands, outer, holes=(), sample_step=0.5, thread_width=0.4):
    """Sample-based geometric *thread footprint estimate*, NOT sewn coverage.

    Check horizontal sample points against sewn line segments with nominal
    thread width. It cannot predict thread pull, loft, material or tension.
    """
    if min(sample_step,thread_width)<=0:
        raise ValueError('Sampling and nominal thread width must be positive')
    xs=[p[0] for p in outer]; ys=[p[1] for p in outer]
    sewn=[]
    previous=None
    for c in commands:
        if c.kind=='STITCH' and previous is not None:
            sewn.append(((previous.x,previous.y),(c.x,c.y)))
        if c.kind in ('STITCH','JUMP'):
            previous=c
    total=covered=0
    y=min(ys)+sample_step/2
    while y<max(ys):
        x=min(xs)+sample_step/2
        while x<max(xs):
            if point_inside((x,y),outer,holes):
                total+=1
                for (ax,ay),(bx,by) in sewn:
                    dx=bx-ax; dy=by-ay
                    t=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy>1e-12 else 0
                    if hypot(x-(ax+t*dx),y-(ay+t*dy))<=thread_width/2:
                        covered+=1
                        break
            x+=sample_step
        y+=sample_step
    return dict(samples=total, covered=covered,
                fraction=round(covered/total,4) if total else 0.0,
                nominal_thread_width_mm=thread_width)
