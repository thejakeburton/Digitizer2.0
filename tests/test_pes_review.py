import tempfile
import unittest
from pathlib import Path


class PESPreviewTests(unittest.TestCase):
    def test_render_is_from_actual_exported_pes(self):
        from digitizer.engine import rectangle_tatami
        from digitizer.export import write_pes
        from digitizer.pes_review import decode_pes,pes_metrics,render_pes
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            target=directory/"test.pes"
            write_pes(rectangle_tatami(15,8,underlay=False),target)
            steps=decode_pes(target)
            self.assertGreater(sum(name=="STITCH" for name,_,_ in steps),30)
            self.assertLessEqual(pes_metrics(steps)["max_sewn_stitch_mm"],2.6)
            render_pes(steps,["#222222"],directory/"sewn.png")
            render_pes(steps,["#222222"],directory/"jumps.png",show_jumps=True)
            self.assertGreater((directory/"sewn.png").stat().st_size,100)
            self.assertGreater((directory/"jumps.png").stat().st_size,100)


    def test_hole_routing_avoids_per_row_jump_explosion(self):
        from digitizer.shape import polygon_tatami
        from digitizer.engine import metrics
        outer=[(0,0),(60,0),(60,40),(0,40)]
        hole=[(13,8),(47,8),(47,32),(13,32)]
        steps=polygon_tatami(outer,[hole],spacing=0.4)
        # Regression: old planner jumped across the hole every row (~60).
        self.assertLessEqual(metrics(steps)["JUMP"],10)

    def test_preview_tracks_color_change(self):
        from PIL import Image
        from digitizer.engine import Command
        from digitizer.pes_review import render_pes
        steps=[("JUMP",0,0),("STITCH",10,0),
               ("COLOR_CHANGE",10,0),("JUMP",0,4),("STITCH",10,4)]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"preview.png"
            render_pes(steps,["#ff0000","#0000ff"],path)
            im=Image.open(path)
            self.assertIn((255,0,0),im.getdata())
            self.assertIn((0,0,255),im.getdata())


if __name__=="__main__":
    unittest.main()
