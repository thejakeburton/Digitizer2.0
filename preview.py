"""Lightweight SVG path visualization. Solid = sewn, dashed = needle jump."""
from html import escape


def save_svg(commands, path, padding=3, scale=12):
    pts = [c for c in commands if c.kind in ('JUMP', 'STITCH')]
    if not pts:
        raise ValueError('Empty stitch plan')
    w = (max(p.x for p in pts) + padding * 2) * scale
    h = (max(p.y for p in pts) + padding * 2) * scale
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}">',
           '<rect width="100%" height="100%" fill="#f5f5f5"/>']
    last = None
    for c in pts:
        here = ((c.x + padding)*scale, (c.y + padding)*scale)
        if last is not None:
            x1,y1 = last
            x2,y2 = here
            color = '#a8a8a8' if c.kind == 'JUMP' else '#222222'
            dash = ' stroke-dasharray="3 5"' if c.kind == 'JUMP' else ''
            svg.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="1.2"{dash}/>')
        last = here
    svg.append('</svg>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
