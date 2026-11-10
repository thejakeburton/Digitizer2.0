"""Review actual PES needle commands; do not confuse travel with sewn thread.

Creates two separate previews: sewn-only and with non-sewn jumps marked red.
This is a geometric stitch rendering, not a fabric/thread physics simulation.
"""
from collections import Counter
from math import hypot
from pathlib import Path


def decode_pes(path):
    import pyembroidery as pe
    pattern=pe.read_pes(str(path))
    decoded=[]
    for x,y,command in pattern.stitches:
        kind=command & pe.COMMAND_MASK
        if kind==pe.STITCH:
            name="STITCH"
        elif kind==pe.JUMP:
            name="JUMP"
        elif kind==pe.COLOR_CHANGE:
            name="COLOR_CHANGE"
        elif kind==pe.END:
            name="END"
        elif kind==pe.TRIM:
            name="TRIM"
        else:
            name=f"OTHER_{kind}"
        decoded.append((name,float(x)/10.,float(y)/10.))
    return decoded


def pes_metrics(steps):
    counts=dict(Counter(name for name,x,y in steps))
    last=None
    max_stitch=0.
    max_jump=0.
    sewn_mm=0.
    jump_mm=0.
    for name,x,y in steps:
        if last is not None and name in ("STITCH","JUMP"):
            distance=hypot(x-last[0],y-last[1])
            if name=="STITCH":
                sewn_mm+=distance
                max_stitch=max(max_stitch,distance)
            else:
                jump_mm+=distance
                max_jump=max(max_jump,distance)
        if name in ("STITCH","JUMP","TRIM"):
            last=(x,y)
    return {"commands":counts,"max_sewn_stitch_mm":round(max_stitch,2),
            "max_jump_mm":round(max_jump,2),
            "sewn_distance_mm":round(sewn_mm,1),
            "nonsewn_jump_distance_mm":round(jump_mm,1)}


def render_pes(steps, colors, destination, show_jumps=False, scale=10):
    from PIL import Image, ImageDraw
    points=[(x,y) for name,x,y in steps if name in ("STITCH","JUMP")]
    if not points:
        raise ValueError("No needle movements")
    x0=min(x for x,y in points)
    y0=min(y for x,y in points)
    x1=max(x for x,y in points)
    y1=max(y for x,y in points)
    margin=20
    width=int((x1-x0)*scale)+2*margin+1
    height=int((y1-y0)*scale)+2*margin+1
    if max(width,height)>7000:
        raise ValueError("Preview is too large")
    img=Image.new("RGB",(width,height),(239,239,239))
    draw=ImageDraw.Draw(img)
    last=None
    index=0
    for name,x,y in steps:
        here=(round((x-x0)*scale+margin),round((y-y0)*scale+margin))
        if name=="COLOR_CHANGE":
            index+=1
        elif name=="STITCH" and last is not None:
            color=colors[min(index,len(colors)-1)]
            draw.line((last,here),fill=color,width=max(1,round(scale*0.35)))
        elif name=="JUMP" and last is not None and show_jumps:
            # Red means MOVEMENT WITHOUT SEWING, not an embroidery color.
            draw.line((last,here),fill=(235,60,65),width=1)
        if name in ("STITCH","JUMP","TRIM"):
            last=here
    img.save(destination)
