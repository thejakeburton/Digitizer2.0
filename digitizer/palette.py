"""Conservative antialias-color cleanup for flat-color illustrations.

Detect solid-area palette colors using 3x3 exact-color cores. Only assign
fringe colors if they fit a linear blend of two detected solids. Reject
unexplained colors rather than inventing or silently erasing details.
"""
import numpy as np
import cv2


def _color_tuple(rgb):
    return tuple(int(x) for x in rgb)


def recover_flat_palette(rgb, max_colors=12, tolerance=18.0,
                         max_unexplained_fraction=0.005):
    """Return (new_rgb, report). RGB input is HxWx3 uint8.

    This deliberately does not solve photos, gradients, or full automatic
    digitizing. Colors with no solid 3x3 area are unconfirmed, not guessed.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB image")
    height,width=rgb.shape[:2]
    unique, counts=np.unique(rgb.reshape(-1,3),axis=0,return_counts=True)
    if len(unique)<=max_colors:
        return rgb.copy(), {"input_colors":len(unique),"output_colors":len(unique),
                            "changed_pixels":0,"unexplained_pixels":0}

    candidates=[]
    # Need at least one solid 3x3 pixel core; this distinguishes solid
    # intentional colors from the 1-pixel antialias fringe in ordinary art.
    for color,count in zip(unique,counts):
        mask=cv2.inRange(rgb,color,color)
        core=cv2.erode(mask,np.ones((3,3),np.uint8),
                       borderType=cv2.BORDER_CONSTANT,borderValue=0)
        if np.any(core):
            candidates.append((_color_tuple(color),int(count)))
    candidates.sort(key=lambda a:(-a[1],a[0]))
    if not candidates or len(candidates)>max_colors:
        raise ValueError("Cannot recover a reliable flat-color palette; "
                         "solid regions missing or too many colors")

    palette=np.asarray([c for c,n in candidates],dtype=np.float64)
    pixels=rgb.reshape(-1,3).astype(np.float64)
    # Pick nearest solid color. A pixel may only be changed if it is
    # close to the straight-line blend between two solid colors.
    distances=((pixels[:,None,:]-palette[None,:,:])**2).sum(axis=2)
    nearest=distances.argmin(axis=1)
    nearest_distance=np.sqrt(distances[np.arange(len(pixels)),nearest])
    acceptable=nearest_distance<=tolerance

    # Antialiased pixels between two solids can be far from *both* anchors.
    # Check perpendicular distance to the RGB line segment between anchors.
    if len(palette)>1:
        for i in range(len(palette)):
            for j in range(i+1,len(palette)):
                a,b=palette[i],palette[j]
                ab=b-a
                d2=float(np.dot(ab,ab))
                if d2<1:
                    continue
                t=np.clip(((pixels-a)@ab)/d2,0.,1.)
                projection=a+t[:,None]*ab
                residual=np.linalg.norm(pixels-projection,axis=1)
                acceptable |= residual<=tolerance

    unexplained=int(np.count_nonzero(~acceptable))
    if unexplained>max(1,int(len(pixels)*max_unexplained_fraction)):
        raise ValueError(
            f"Antialias cleanup refused: {unexplained} pixels do not match "
            "solid colors or their edge blends. Preserve source art and "
            "select a different import method."
        )
    if unexplained:
        # Even a small unexplained residual would have to be arbitrarily
        # assigned a color, so fail safely rather than silently erase it.
        raise ValueError(f"Antialias cleanup found {unexplained} unexplained pixels")
    mapped=palette[nearest].astype(np.uint8).reshape(height,width,3)
    changed=int(np.count_nonzero(np.any(mapped!=rgb,axis=2)))
    return mapped, {"input_colors":len(unique),"output_colors":len(palette),
                    "changed_pixels":changed,"unexplained_pixels":0,
                    "palette":["#"+"".join(f"{v:02x}" for v in c)
                               for c,n in candidates]}
