"""Deathwish Digitizer 2.0 — test-only Mac GUI (fill stitches only)."""
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

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
        self.source_image = None    # PIL image, loaded once per file
        self.preview_image = None   # PIL image of the decoded PES
        self.commands = None
        self.colors = None
        self.photo = None
        self.preview_photo = None
        self.busy = False
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
        self.open_button = ttk.Button(toolbar, text="Open Image", command=self.open_image)
        self.open_button.pack(side="left", padx=(0, 8))
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
    def _display(canvas, image):
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 20 or height < 20:
            return None
        thumbnail = image.copy()
        thumbnail.thumbnail((max(1, width - 16), max(1, height - 16)), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(thumbnail)
        canvas.delete("all")
        canvas.create_image(width // 2, height // 2, anchor="center", image=photo)
        return photo

    def _show_source(self):
        if self.source_image is not None:
            photo = self._display(self.original_canvas, self.source_image)
            if photo is not None:
                self.photo = photo

    def _show_preview(self):
        if self.preview_image is not None:
            photo = self._display(self.stitch_canvas, self.preview_image)
            if photo is not None:
                self.preview_photo = photo

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.open_button.config(state=state)
        self.generate_button.config(state=state)
        if busy:
            self.export_button.config(state="disabled")

    def open_image(self):
        path = filedialog.askopenfilename(title="Choose flat-color artwork",
            filetypes=[("Artwork", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        try:
            with Image.open(path) as source:
                loaded = source.convert("RGB")
        except Exception as error:
            messagebox.showerror("Could not open image", str(error))
            return
        self.image_path = path
        self.source_image = loaded
        self.commands = None
        self.colors = None
        self.preview_image = None
        self.preview_photo = None
        self.export_button.config(state="disabled")
        self.stitch_canvas.delete("all")
        self.status.set("Loaded " + Path(path).name + ". Click Generate Stitches.")
        self._show_source()

    def _settings(self):
        try:
            width = float(self.width_var.get())
            spacing = float(self.spacing_var.get())
            length = float(self.length_var.get())
        except ValueError:
            raise ValueError("Width, row spacing and stitch length must be numbers.") from None
        if not 1 <= width <= 300 or not 0.15 <= spacing <= 2.0 or not 0.5 <= length <= 8.0:
            raise ValueError("Width: 1–300 mm; row spacing: 0.15–2.0 mm; stitch length: 0.5–8.0 mm.")
        return width, spacing, length

    def generate(self):
        if self.busy:
            return
        if not self.image_path:
            messagebox.showinfo("Open an image", "Select artwork first.")
            return
        try:
            width, spacing, length = self._settings()
        except ValueError as error:
            messagebox.showerror("Check settings", str(error))
            return
        self.commands = None
        self.colors = None
        self._set_busy(True)
        self.status.set("Generating stitches… this can take a moment for large artwork.")
        worker = threading.Thread(
            target=self._generate_worker,
            args=(self.image_path, width, spacing, length, self.cleanup_var.get()),
            daemon=True)
        worker.start()

    def _generate_worker(self, path, width, spacing, length, cleanup):
        """Runs off the UI thread. Must not touch any Tk widgets."""
        try:
            regions = image_regions(path, width_mm=width, antialias_cleanup=cleanup)
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
                    preview = image.convert("RGB").copy()
            result = {
                "regions": len(regions),
                "commands": commands,
                "colors": colors,
                "preview": preview,
                "info": pes_metrics(decoded),
            }
            self.after(0, self._generate_done, path, result, None)
        except Exception as error:
            self.after(0, self._generate_done, path, None, error)

    def _generate_done(self, path, result, error):
        self._set_busy(False)
        if path != self.image_path:
            return  # a different image was loaded while this one was running
        if error is not None:
            self.preview_image = None
            self.preview_photo = None
            self.stitch_canvas.delete("all")
            messagebox.showerror("Could not digitize artwork", str(error))
            self.status.set("Unable to generate stitches: " + str(error))
            return
        self.commands, self.colors = result["commands"], result["colors"]
        self.preview_image = result["preview"]
        self._show_preview()
        counts = result["info"]["commands"]
        self.status.set(
            f"{result['regions']} regions | {len(self.colors)} thread blocks | "
            f"{counts.get('STITCH', 0)} stitches | "
            f"{counts.get('JUMP', 0)} jumps | "
            f"{counts.get('TRIM', 0)} trims")
        self.export_button.config(state="normal")

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
