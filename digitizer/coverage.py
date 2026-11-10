"""Estimate nominal sewn-thread footprint against a source flat-color PNG.

This is intentionally a geometrical estimate: user-specified thread width,
no tension, distortion, push/pull, fabric, or thread texture. A pale magenta
overlay marks intended colored pixels outside any thread footprint.
"""
import numpy as np
from PIL import Image, ImageDraw


def coverage_from_pes(source_path, decoded, palette, width_mm,
                      destination, nominal_thread_width_mm=0.40):
    source=np.asarray(Image.open(source_path).convert("RGB"))
    h,w=source.shape[:2]
    mm_to_px=w/width_mm
    masks=[Image.new("L",(w,h),0) for _ in palette]
    draw=[ImageDraw.Draw(mask) for mask in masks]
    last=None
    color_index=0
    stroke=max(1,round(nominal_thread_width_mm*mm_to_px))
    for kind,x,y in decoded:
        at=(round(x*mm_to_px),round(y*mm_to_px))
        if kind=="COLOR_CHANGE":
            color_index+=1
        elif kind=="STITCH" and last is not None:
            draw[min(color_index,len(draw)-1)].line(
                (last,at),fill=255,width=stroke)
        if kind in ("JUMP","STITCH","TRIM"):
            last=at
    report={}
    overlay=source.copy()
    for color, mask in zip(palette,masks):
        rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
        expected=np.all(source==np.asarray(rgb,dtype=np.uint8),axis=2)
        sewn=np.asarray(mask)>0
        total=int(expected.sum())
        hit=int((expected & sewn).sum())
        uncovered=expected & ~sewn
        overlay[uncovered]=[255,40,210]
        report[color]={"intended_pixels":total,"nominally_covered_pixels":hit,
                       "estimated_coverage_fraction":round(hit/total,4)
                       if total else None}
    Image.fromarray(overlay).save(destination)
    return {"nominal_thread_width_mm":nominal_thread_width_mm,
            "coverage_by_color":report,
            "warning":"Magenta estimates geometric uncovered pixels, not guaranteed physical gaps."}
