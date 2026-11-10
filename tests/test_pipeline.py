"""End-to-end strict-palette image import through PES export."""
import tempfile
import unittest
from pathlib import Path


class TestEndToEnd(unittest.TestCase):
    def test_two_color_png_to_pes(self):
        try:
            from PIL import Image, ImageDraw
            import pyembroidery as pe
        except ImportError:
            raise unittest.SkipTest("Image and PES dependencies required")
        from digitizer.image import image_regions
        from digitizer.layers import plan_layers
        from digitizer.export import write_pes
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"test.png"
            target=Path(temp)/"test.pes"
            im=Image.new("RGB",(80,50),(0,0,0))
            ImageDraw.Draw(im).rectangle((20,12,59,37),fill=(255,210,0))
            im.save(source)
            regions=image_regions(source,width_mm=40)
            commands,colors=plan_layers(regions)
            write_pes(commands,target,colors=colors)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size,100)
            decoded=pe.read_pes(str(target))
            decoded_colors=[thread.get_hex_color().lower() for thread in decoded.threadlist]
            self.assertGreaterEqual(len(decoded_colors),2)
            self.assertGreater(len(decoded.stitches),50)

    def test_export_requires_matching_thread_count(self):
        from digitizer.engine import Command
        from digitizer.export import write_pes
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_pes([Command("COLOR_CHANGE",0,0),Command("END",0,0)],
                          Path(tmp)/"bad.pes",colors=["#000000"])

if __name__=="__main__":
    unittest.main()
