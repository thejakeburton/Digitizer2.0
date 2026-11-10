# Deathwish Digitizer 2.0

Embroidery-first architecture. **This is a geometry/stitch-planning prototype, not an automatic image digitizer or finished Mac application.**

## Try it

```bash
python3 main.py --out output
python3 -m unittest discover -s tests -v
```

Open `output/rectangle.svg` in a browser. Black solid lines represent sewn stitches; gray dashed lines are jumps **and are not sewn**. `output/metrics.json` reports stitch and jump counts, travel distances, and maximum stitch lengths.

To generate a PES test file:

```bash
python3 -m pip install pyembroidery
python3 main.py --pes --out output
```

**Do not use this prototype for production embroidery without inspecting the PES in an embroidery viewer and doing a controlled scrap sew-out.** SVG is a command visualization, not a fabric or thread-coverage prediction.

## Architectural rules

1. Image segmentation (future) remains independent of stitch planning.
2. Planner emits explicit `STITCH`, `JUMP`, `COLOR_CHANGE`, `END` commands.
3. Exporters preserve stitch sequence and convert mm to PES units.
4. Every change must have deterministic tests and a command visualization before Mac packaging.
5. Preserve successful recognition concepts without copying the old simplistic fill generator.

## Milestones

- **M0 (baseline):** staggered rectangle tatami and SVG command viewer; every row used a JUMP (46 jumps on the default rectangle).
- **M1 (current):** serpentine row routing with sewn connections along the boundary, inset edge-walk underlay, geometric row coverage checks, and max stitch/jump metrics. Default rectangle now needs 2 jumps total, or 1 with underlay disabled.
- **M2 (next):** irregular shapes and holes, safe clipped travel, edge compensation, coverage estimation and broader test shapes.
- **M3:** multicolor layer planning and detail-preserving image extraction.
- **M4:** satin and running stitch types, then Mac UI and packaging.

## Known limitations

- The edge-walk underlay is a prototype; its support and effectiveness on actual fabric are **not validated**.
- Row-edge connectors are sewn and may create buildup on some fabrics.
- No density compensation, fabric physics, pull compensation, object clipping, or automatic stitch-type assignment.
- No production PES sew-out has been verified.
