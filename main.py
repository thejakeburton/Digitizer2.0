"""Reproducible embroidery geometry benchmarks.

Examples:
  python main.py --shape rectangle --out output
  python main.py --shape l-shape --out output
  python main.py --shape donut --out output
"""
import argparse
import json
from pathlib import Path
from digitizer.engine import rectangle_tatami, metrics
from digitizer.shape import polygon_tatami, coverage_report
from digitizer.preview import save_svg


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--width', type=float, default=35)
    p.add_argument('--height', type=float, default=18)
    p.add_argument('--spacing', type=float, default=0.4)
    p.add_argument('--stitch-length', type=float, default=2.5)
    p.add_argument('--shape', choices=('rectangle','polygon-rectangle','l-shape','donut'),
                   default='rectangle')
    p.add_argument('--edge-inset', type=float, default=0.0)
    p.add_argument('--out', default='output')
    p.add_argument('--pes', action='store_true', help='Also write PES (requires pyembroidery)')
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    corners = [(0,0),(a.width,0),(a.width,a.height),(0,a.height)]
    holes = []
    if a.shape == 'rectangle':
        cmds = rectangle_tatami(a.width,a.height,a.spacing,a.stitch_length)
    else:
        if a.shape == 'l-shape':
            corners=[(0,0),(a.width,0),(a.width,a.height*0.4),
                     (a.width*0.4,a.height*0.4),
                     (a.width*0.4,a.height),(0,a.height)]
        elif a.shape == 'donut':
            holes=[[(a.width*0.35,a.height*0.3),
                    (a.width*0.65,a.height*0.3),
                    (a.width*0.65,a.height*0.7),
                    (a.width*0.35,a.height*0.7)]]
        cmds=polygon_tatami(corners,holes,spacing=a.spacing,
                            stitch_length=a.stitch_length,edge_inset=a.edge_inset)
    filename=a.shape
    save_svg(cmds,out/(filename+'.svg'))
    (out/(filename+'_stitches.json')).write_text(
        json.dumps([c.__dict__ for c in cmds],indent=2))
    report=metrics(cmds)
    if a.shape!='rectangle':
        report['geometric_coverage']=coverage_report(
            cmds,corners,holes,sample_step=0.7,thread_width=0.4)
    (out/(filename+'_metrics.json')).write_text(json.dumps(report,indent=2))
    if a.pes:
        from digitizer.export import write_pes
        write_pes(cmds,out/(filename+'.pes'))
    print(json.dumps(report,indent=2))
    print('Preview:',out/(filename+'.svg'))


if __name__=='__main__':
    main()
