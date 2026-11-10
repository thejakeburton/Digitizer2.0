"""Run the first reproducible embroidery benchmark.

python main.py --width 35 --height 18 --out output
"""
import argparse
import json
from pathlib import Path
from digitizer.engine import rectangle_tatami, metrics
from digitizer.preview import save_svg


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--width', type=float, default=35)
    p.add_argument('--height', type=float, default=18)
    p.add_argument('--spacing', type=float, default=0.4)
    p.add_argument('--stitch-length', type=float, default=2.5)
    p.add_argument('--out', default='output')
    p.add_argument('--pes', action='store_true', help='Also write PES (requires pyembroidery)')
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cmds = rectangle_tatami(a.width, a.height, a.spacing, a.stitch_length)
    save_svg(cmds, out / 'rectangle.svg')
    (out / 'stitches.json').write_text(json.dumps([c.__dict__ for c in cmds], indent=2))
    report = metrics(cmds)
    (out / 'metrics.json').write_text(json.dumps(report, indent=2))
    if a.pes:
        from digitizer.export import write_pes
        write_pes(cmds, out / 'rectangle.pes')
    print(json.dumps(report, indent=2))
    print('Preview:', out / 'rectangle.svg')


if __name__ == '__main__':
    main()
