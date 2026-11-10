# Deathwish Digitizer 2.0

Fill-only embroidery architecture for paintball headbands, with an experimental image-to-PES command line pipeline. **This is not a production-ready automatic digitizer or a finished Mac application.**

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

### Import controlled flat-color artwork

Install the image dependencies:

```bash
python3 -m pip install pillow numpy opencv-python-headless pyembroidery
```

For flat-color PNGs with more than a few antialiased edge shades:

```bash
python3 main.py --image your-artwork.png --width 60 --antialias-cleanup --pes --out output
```

The `--antialias-cleanup` flag is **opt-in**. It identifies solid 3x3 color cores, assigns plausible antialias blends to those colors, and refuses ambiguous pixels. It deliberately does not flatten photographs or arbitrary gradients. Omit the flag for exact-palette/pixel-art input. Always inspect region count, thread colors and SVG preview, because pixel contour extraction and stitch order are still experimental.

**Do not use this prototype for production embroidery without inspecting the PES in an embroidery viewer and doing a controlled scrap sew-out.** SVG is a command visualization, not a fabric or thread-coverage prediction.

## Mac fill-only test app (Linux-packaged, no macOS runner)

The [Mac Test App workflow](https://github.com/thejakeburton/Digitizer2.0/actions/workflows/mac-build.yml)
runs on **Ubuntu**, so it no longer waits for GitHub-hosted Mac runners. Every
successful run uploads an artifact named `deathwish-digitizer-2-mac-test`.
Download it, unzip the artifact and the contained `Deathwish-Digitizer-2-Mac-Test.zip`,
then open `Deathwish Digitizer 2 Test.app` on your Mac.

**Important:** This is a **bootstrap Mac app**, not a fully self-contained
PyInstaller executable. On the **first launch only**, it needs internet access
and **Python 3.10+ with Tkinter** already installed on your Mac. The official
[python.org macOS installer](https://www.python.org/downloads/macos/) includes
Tkinter. The app creates a private virtual environment under
`~/Library/Application Support/Deathwish Digitizer 2 Test/` and installs its
libraries there. It never requires GitHub's macOS build service. If launch
fails, see `~/Library/Application Support/Deathwish Digitizer 2 Test/launch.log`.

Since the bundle is unsigned, macOS may block it initially. In Finder,
Control-click the app and choose **Open**, or use
System Settings → Privacy & Security → Open Anyway. Do not disable Gatekeeper.

1. Open a flat-color PNG or JPG (not a photograph).
2. Set design width, fill row spacing and stitch length.
3. Click **Generate Stitches** to view the actual PES stitch commands.
4. Choose **Export PES**, inspect the file in Artspira, and verify dimensions,
   thread colors, stitch coverage and travel before a scrap-fabric sew-out.

There is deliberately **no satin option**. The preview is geometric, not
fabric-accurate; complex imagery may still fail at import. This is a
test app, not a production-ready digitizer.

## Visual review of the exported PES

Every successful GitHub Actions **Tests** run produces an artifact named
`pes-stitch-review`. In the workflow run, open **Artifacts** and download it.

The artifact contains:
- `source.png` — the controlled two-color test image
- `test.pes` — an actual PES export to inspect in Artspira
- `actual-sewn-only.png` — sewn stitches decoded back from the PES
- `actual-with-jumps.png` — identical preview, with **non-sewn** travel in red
- `estimated-coverage.png` — magenta indicates nominal uncovered areas
- `report.json` — jumps, trims, distances, nominal coverage per thread

The coverage image assumes 0.4mm nominal thread footprint and uses pixel
sampling. It is **not** proof of physical thread gaps, and the synthetic shape
is **not** representative of complex logo or illustration results. The build
is not yet cleared for production or a polished Mac interface.

## Product scope

**Fill stitches only.** All artwork regions use tatami-style fills, including fine regions where geometry permits. Vector tracing and detail retention remain essential. Automatic satin and decorative running-stitch generation are out of scope. Travel and underlay stitches may still use ordinary straight stitch commands; this is not a satin-feature commitment.

Acceptance priorities: (1) preserve illustration details, (2) no unexplained uncovered regions or stray stitched paths, (3) controlled tatami texture without conspicuous ribbing, (4) accurate PES readback visualization, (5) sane routing and color order. Validate on actual headband fabric before production.

## Architectural rules

1. Image segmentation remains independent of stitch planning.
2. Planner emits explicit `STITCH`, `JUMP`, `COLOR_CHANGE`, `END` commands.
3. Exporters preserve stitch sequence and convert mm to PES units.
4. Every change must have deterministic tests and a command visualization before Mac packaging.
5. Preserve successful recognition concepts without copying the old simplistic fill generator.

## Milestones

- **M0 (baseline):** staggered rectangle tatami and SVG command viewer; every row used a JUMP (46 jumps on the default rectangle).
- **M1:** serpentine row routing with sewn connections along the boundary, inset edge-walk underlay, geometric row coverage checks, and max stitch/jump metrics. Default rectangle now needs 2 jumps total, or 1 with underlay disabled.
- **M2:** irregular shapes and holes, safe clipped travel, horizontal edge inset, geometric coverage sampling and test shapes.
- **M3 (current, experimental):** explicit multicolor layer planning, flat-color PNG extraction, opt-in guarded antialias cleanup and PES readback tests.
- **M4 (planned):** improve fill density, stagger, and coverage, validate real headband artwork, then Mac UI and packaging. No satin generation.

## Known limitations

- The edge-walk underlay is a prototype; its support and effectiveness on actual fabric are **not validated**.
- Row-edge connectors are sewn and may create buildup on some fabrics.
- Horizontal insets are not fabric-specific pull compensation. No fabric physics or automatic stitch-type assignment.
- Palette cleanup requires flat solid areas, may reject isolated tiny details, and does not yet handle complex multicolor illustrations.
- Image-derived region layering is heuristic and must be inspected.
- No production PES sew-out has been verified.
