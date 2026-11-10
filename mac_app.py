"""Deathwish Digitizer 2.0 — test-only Mac GUI (fill stitches only)."""
import json
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from digitizer.engine import metrics
from digitizer.export import write_pes
from digitizer.image import image_regions
from digitizer.layers import plan_layers
from digitizer.pes_review import decode_pes, pes_metrics, render_pes


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Deathwish Digitizer 2.0 | Fill Test")
        self.geometry("1050x750")
        self.minsize(780, 520)
        self.image_path = None
        self.commands = None
        self.colors = None
        self.photo = None
        self.preview_photo = None
        self.width_var = tk.StringVar(value="60")
        self.spacing_var = tk.StringVar(value="0.40")
        self.length_var = tk.StringVar(value="2.5")
        self.cleanup_var = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Open a flat-color PNG or JPG to begin.")
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        toolbar = ttk.Frame(root)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Open Image", command=self.open_image).pack(side="left", padx=(0, 8))
        self.generate_button = ttk.Button(toolbar, text="Generate Stitches", command=self.generate)
        self.generate_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(toolbar, text="Export PES", command=self.export, state="disabled")
        self.export_button.pack(side="left", padx=8)
        ttk.Label(root, textvariable=self.status, wraplength=900).pack(fill="x", pady=(10, 10))
        options = ttk.LabelFrame(root, text="Fill-stitch settings (experimental)", padding=10)
        options.pack(fill="x")
        for label, var in (("Design width (mm)", self.width_var),
                           ("Row spacing (mm)", self.spacing_var),
                           ("Stitch length (mm)", self.length_var)):
            item = ttk.Frame(options)
            item.pack(side="left", padx=(0, 16))
            ttk.Label(item, text=label).pack(anchor="w")
            ttk.Entry(item, textvariable=var, width=12).pack(anchor="w")
        ttk.Checkbutton(options, text="Clean antialiased edges", variable=self.cleanup_var).pack(side="left", padx=12)
        panes = ttk.Panedwindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=12)
        left = ttk.LabelFrame(panes, text="Source artwork", padding=8)
        right = ttk.LabelFrame(panes, text="Actual PES stitch preview (not source pixels)", padding=8)
        panes.add(left, weight=1)
        panes.add(right, weight=1)
        self.original_canvas = tk.Canvas(left, background="#e8e8e8", highlightthickness=0)
        self.original_canvas.pack(fill="both", expand=True)
        self.stitch_canvas = tk.Canvas(right, background="#f0f0f0", highlightthickness=0)
        self.stitch_canvas.pack(fill="both", expand=True)
        self.original_canvas.bind("<Configure>", lambda event: self._show_source())
        self.stitch_canvas.bind("<Configure>", lambda event: self._show_preview())
        ttk.Label(root, text="TEST BUILD: flat-color artwork only. Preview shows PES commands, not physical thread or fabric. "
                  "Inspect PES in Artspira before any scrap sew-out.", wraplength=950).pack(fill="x")

    @staticmethod
    def _display(canvas, image, tag):
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 20 or height < 20:
            return None
        thumbnail = image.copy()
        thumbnail.thumbnail((max(1, width-16), max(1, height-16)), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(thumbnail)
        canvas.delete("all")
        canvas.create_image(width//2, height//2, anchor="center", image=photo)
        return photo

    def _show_source(self):
        if self.image_path:
            try:
                with Image.open(self.image_path) as source:
                    self.photo = self._display(self.original_canvas, source.convert("RGB"), "source")
            except Exception:
                pass

    def _show_preview(self):
        if getattr(self, "preview_image", None) is not None:
            self.preview_photo = self._display(self.stitch_canvas, self.preview_image, "preview")

    def open_image(self):
        path = filedialog.askopenfilename(title="Choose flat-color artwork",
            filetypes=[("Artwork", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        self.image_path = path
        self.commands = None
        self.colors = None
        self.preview_image = None
        self.export_button.config(state="disabled")
        self.stitch_canvas.delete("all")
        self.status.set("Loaded " + Path(path).name + ". Click Generate Stitches.")
        self._show_source()

    def _settings(self):
        width = float(self.width_var.get())
        spacing = float(self.spacing_var.get())
        length = float(self.length_var.get())
        if not 1 <= width <= 300 or not 0.15 <= spacing <= 2.0 or not 0.5 <= length <= 8.0:
            raise ValueError("Width: 1–300 mm; row spacing: 0.15–2.0 mm; stitch length: 0.5–8.0 mm.")
        return width, spacing, length

    def generate(self):
        if not self.image_path:
            messagebox.showinfo("Open an image", "Select artwork first.")
            return
        self.export_button.config(state="disabled")
        self.commands = None
        self.update_idletasks()
        try:
            width, spacing, length = self._settings()
            regions = image_regions(self.image_path, width_mm=width,
                                    antialias_cleanup=self.cleanup_var.get())
            commands, colors = plan_layers(regions, spacing=spacing, stitch_length=length)
            # Generate and re-read the actual PES to avoid drawing a misleading
            # planned-preview that hides exporter command conversions.
            with tempfile.TemporaryDirectory() as folder:
                pes = Path(folder) / "preview.pes"
                png = Path(folder) / "preview.png"
                write_pes(commands, pes, colors=colors)
                decoded = decode_pes(pes)
                render_pes(decoded, colors, png, scale=9)
                with Image.open(png) as image:
                    self.preview_image = image.convert("RGB").copy()
            self.commands, self.colors = commands, colors
            self._show_preview()
            info = pes_metrics(decoded)
            self.status.set(
                f"{len(regions)} regions | {len(colors)} thread blocks | "
                f"{info['commands'].get('STITCH',0)} stitches | "
                f"{info['commands'].get('JUMP',0)} jumps | "
                f"{info['commands'].get('TRIM',0)} trims")
            self.export_button.config(state="normal")
        except Exception as error:
            self.preview_image = None
            self.stitch_canvas.delete("all")
            messagebox.showerror("Could not digitize artwork", str(error))
            self.status.set("Unable to generate stitches: " + str(error))

    def export(self):
        if self.commands is None:
            return
        destination = filedialog.asksaveasfilename(title="Save Brother PES test",
            defaultextension=".pes", filetypes=[("Brother PES", "*.pes")],
            initialfile="Deathwish-test.pes")
        if not destination:
            return
        try:
            write_pes(self.commands, Path(destination), colors=self.colors)
            self.status.set("Exported " + Path(destination).name
                            + " — inspect in Artspira before sewing.")
            messagebox.showinfo("Export complete", "PES saved. Check the stitch preview "
                                "and thread colors in Artspira before using scrap fabric.")
        except Exception as error:
            messagebox.showerror("Export failed", str(error))


if __name__ == "__main__":
    Application().mainloop()
