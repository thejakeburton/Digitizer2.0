"""Controlled color-image -> embroidery region extraction.

Default mode uses exact RGB colors. Optional guarded antialias cleanup
recovers only solid-area colors and their plausible edge mixtures.
A pixel is assigned to exactly one color. Connected contour hierarchy becomes
outer geometry and holes. Background color is determined by border prevalence,
then sewn first. This module does NOT attempt production-grade digitization.
"""
from collections import Counter
from pathlib import Path

from .layers import Region


def image_regions(path, width_mm=60., min_area_px=9, max_colors=12,
                  antialias_cleanup=False):
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Image import requires pillow, numpy and opencv-python-headless") from exc
    if not 0 < width_mm <= 300:
        raise ValueError("Design width must be between 0 and 300mm")
    with Image.open(path) as img:
        # Transparent pixels become white. RGBA compositing prevents treating
        # invisible RGB values as extra thread colors.
        rgba=img.convert("RGBA")
        base=Image.new("RGBA",rgba.size,(255,255,255,255))
        base.alpha_composite(rgba)
        rgb=np.asarray(base.convert("RGB"))
    height,width=rgb.shape[:2]
    if width<3 or height<3 or width*height>4_000_000:
        raise ValueError("Image must be >=3x3 pixels and <=4 million pixels")
    if antialias_cleanup:
        from .palette import recover_flat_palette
        rgb, _ = recover_flat_palette(rgb, max_colors=max_colors)
    colors,counts=np.unique(rgb.reshape(-1,3),axis=0,return_counts=True)
    if len(colors)>max_colors:
        raise ValueError(
            f"Image has {len(colors)} exact colors; this first importer supports "
            f"at most {max_colors}. Reduce the palette before importing."
        )
    border=np.concatenate((rgb[0],rgb[-1],rgb[:,0],rgb[:,-1]))
    background=Counter(map(tuple,border.tolist())).most_common(1)[0][0]
    order=[background]+sorted(
        (tuple(map(int,color)) for color in colors if tuple(color)!=background),
        key=lambda c:(-int(counts[next(i for i,v in enumerate(colors) if tuple(v)==c)]),c)
    )
    mm_per_px=width_mm/width
    result=[]
    for color in order:
        mask=np.all(rgb==np.array(color,dtype=np.uint8),axis=2).astype(np.uint8)*255
        # RETR_CCOMP yields alternating external components / holes.
        contours,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            continue
        hierarchy=hierarchy[0]
        for idx,curve in enumerate(contours):
            if hierarchy[idx][3]!=-1 or cv2.contourArea(curve)<min_area_px:
                continue
            def polygon(contour):
                # Grid-to-mm conversion; no smoothing to conceal missing details.
                epsilon=0.25
                approx=cv2.approxPolyDP(contour,epsilon,True)
                return tuple((float(p[0][0])*mm_per_px,
                              float(p[0][1])*mm_per_px) for p in approx)
            outer=polygon(curve)
            hole_indices=[]
            child=int(hierarchy[idx][2])
            while child!=-1:
                if cv2.contourArea(contours[child])>=min_area_px:
                    hole_indices.append(child)
                child=int(hierarchy[child][0])
            holes=tuple(polygon(contours[h]) for h in hole_indices)
            if len(outer)>=3:
                result.append(Region("#"+"".join(f"{int(c):02x}" for c in color),
                                     outer,holes))
    if not result:
        raise ValueError("No image regions met the minimum area")
    return result
