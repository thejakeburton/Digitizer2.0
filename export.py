"""Optional PES writer; this is intentionally isolated from planning code."""

def write_pes(commands, path):
    try:
        import pyembroidery as pe
    except ImportError as exc:
        raise RuntimeError('PES export requires: pip install pyembroidery') from exc
    pattern = pe.EmbPattern()
    pattern.add_thread({'name': 'Test Black', 'color': '#222222'})
    for c in commands:
        if c.kind == 'STITCH':
            pattern.add_stitch_absolute(pe.STITCH, c.x * 10, c.y * 10)
        elif c.kind == 'JUMP':
            pattern.add_stitch_absolute(pe.JUMP, c.x * 10, c.y * 10)
    pattern.add_command(pe.END)
    pe.write_pes(pattern, str(path))
