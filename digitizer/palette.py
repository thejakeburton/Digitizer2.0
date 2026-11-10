"""Conservative antialias-color cleanup for flat-color illustrations.

Detect solid-area palette colors using 3x3 exact-color cores. Only assign
fringe colors if they fit a linear blend of two detected solids. Reject
unexplained colors rather than inventing or silently erasing details.
"""
import numpy as np


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
    # Detect all uniform 3x3 cores in one image-sized pass rather than
    # scanning the entire image independently for each antialias shade.
    core=rgb[1:-1,1:-1]
    uniform=np.ones((height-2,width-2),dtype=bool)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dy==0 and dx==0:
                continue
            uniform &= np.all(core==rgb[1+dy:height-1+dy,
                                         1+dx:width-1+dx],axis=2)
    core_colors=np.unique(core[uniform],axis=0).tolist()
    counts_by_color={_color_tuple(c):int(n) for c,n in zip(unique,counts)}
    candidates=[(_color_tuple(c),counts_by_color[_color_tuple(c)])
                for c in core_colors]
    candidates.sort(key=lambda a:(-a[1],a[0]))
    if not candidates or len(candidates)>max_colors:
        raise ValueError("Cannot recover a reliable flat-color palette; "
                         "solid regions missing or too many colors")
    if len(unique)==len(candidates):
        return rgb.copy(), {"input_colors":len(unique),"output_colors":len(unique),
                            "changed_pixels":0,"unexplained_pixels":0}

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
