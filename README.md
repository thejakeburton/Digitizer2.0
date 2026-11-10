# Deathwish Digitizer 2.0

Fresh embroidery-first architecture. **This is a geometry/stitch-planning prototype, not an automatic image digitizer or finished Mac application.** The first milestone isolates a black rectangle tatami fill, measures its jumps, and creates an SVG simulator showing sewn vs travel movement. No UI or image import yet.

## Try it

```bash
python3 main.py --out output
python3 -m unittest discover -s tests -v
```

Open `output/rectangle.svg` in a browser. Black solid lines represent sewn stitches; gray dashed lines are jumps **and are not sewn**. `output/metrics.json` reports stitch/jump counts. To generate a PES test file:

```bash
python3 -m pip install pyembroidery
python3 main.py --pes --out output
```

PES stitch coordinates are 0.1 mm units; the export module handles conversion. **Do not run a machine from this first prototype without inspecting the file in an embroidery viewer and performing a controlled scrap sew-out.**

## Architectural rules

1. Image segmentation (future) will be independent from the sewing planner.
2. The sewing planner emits explicit `STITCH`, `JUMP`, `COLOR_CHANGE` and `END` commands.
3. Exporters must not change the intended stitch sequence.
4. Every change must have a deterministic test and exported preview before packaging a Mac app.
5. Keep proven recognition/tracing concepts, but do not copy the old simplistic fill code.

## Planned milestones

- **M0 (here):** baseline rectangle, staggered tatami rows, per-command visualization, tests.
- **M1:** route neighboring rows with inside-shape travel; add underlay and fill coverage checks. Compare metrics against M0.
- **M2:** irregular contours/holes, clipping, edge compensation, and automated test shapes.
- **M3:** multicolor layer planning and detail preserving image extraction.
- **M4:** satin and running stitches based on geometry, then Mac UI and packaging.

## Known limitations

- Row transitions are JUMPs, not optimized travel; expect many jumps until M1.
- Row spacing is constant and coverage is not yet evaluated against fabric/thread physics.
- No pull compensation, underlay, segmentation, or automatic stitch-type assignment.
- No tested production PES sew-out; SVG is a plan visualization, not a physical prediction.
