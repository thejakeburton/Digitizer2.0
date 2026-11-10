"""Create reviewable PES and stitch-only/jump overlay PNG artifacts."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from digitizer.image import image_regions
from digitizer.layers import plan_layers
from digitizer.export import write_pes
from digitizer.engine import metrics
from digitizer.pes_review import decode_pes,pes_metrics,render_pes
from digitizer.coverage import coverage_from_pes


def main():
    out=Path("review-output")
    out.mkdir(exist_ok=True)
    image=Image.new("RGB",(160,100),(0,0,0))
    d=ImageDraw.Draw(image)
    # Deliberately simple flat-color regression artwork.
    d.rectangle((35,20,125,80),fill=(255,205,0))
    image.save(out/"source.png")
    regions=image_regions(out/"source.png",width_mm=60)
    plan,colors=plan_layers(regions,spacing=0.4,stitch_length=2.5)
    write_pes(plan,out/"test.pes",colors=colors)
    readback=decode_pes(out/"test.pes")
    render_pes(readback,colors,out/"actual-sewn-only.png")
    render_pes(readback,colors,out/"actual-with-jumps.png",show_jumps=True)
    coverage=coverage_from_pes(out/"source.png",readback,colors,60,
                               out/"estimated-coverage.png")
    report={"nominal_coverage":coverage,"source":"Synthetic two-color flat artwork",
            "planned":metrics(plan),"pes_readback":pes_metrics(readback),
            "planned_colors":colors,"regions":len(regions),
            "preview_note":"Red paths in jumps image are NON-SEWN travel; previews are geometry only."}
    (out/"report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
