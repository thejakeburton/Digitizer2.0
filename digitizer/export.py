"""PES writer; only translates planner commands and millimeters to 0.1mm."""
def write_pes(commands, path, colors=None):
    try:
        import pyembroidery as pe
    except ImportError as exc:
        raise RuntimeError("PES export requires: pip install pyembroidery") from exc
    commands=list(commands)
    changes=sum(c.kind=="COLOR_CHANGE" for c in commands)
    if colors is None:
        if changes:
            raise ValueError("Explicit thread colors required for multicolor PES")
        colors=["#222222"]
    if len(colors)!=changes+1:
        raise ValueError("Colors must match embroidery color blocks")
    pattern=pe.EmbPattern()
    for index,color in enumerate(colors):
        pattern.add_thread({"name":f"Color {index+1}","color":color})
    for cmd in commands:
        if cmd.kind=="STITCH":
            pattern.add_stitch_absolute(pe.STITCH,round(cmd.x*10),round(cmd.y*10))
        elif cmd.kind=="JUMP":
            pattern.add_stitch_absolute(pe.JUMP,round(cmd.x*10),round(cmd.y*10))
        elif cmd.kind=="COLOR_CHANGE":
            pattern.add_command(pe.COLOR_CHANGE)
        elif cmd.kind=="END":
            pass
        else:
            raise ValueError(f"Unsupported stitch command: {cmd.kind}")
    pattern.add_command(pe.END)
    pe.write_pes(pattern,str(path))
