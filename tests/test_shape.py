import unittest
from math import hypot
from digitizer.engine import metrics
from digitizer.shape import polygon_tatami, point_inside, scanline_intervals, coverage_report

RECT=[(0,0),(35,0),(35,18),(0,18)]
HOLE=[(12,5),(23,5),(23,13),(12,13)]
L_SHAPE=[(0,0),(25,0),(25,8),(10,8),(10,20),(0,20)]


class TestPolygonEngine(unittest.TestCase):
    def test_rect_all_rows_bounded(self):
        cmds=polygon_tatami(RECT)
        self.assertEqual(cmds[-1].kind,'END')
        self.assertTrue(all(0<=c.x<=35 and 0<=c.y<=18 for c in cmds))
        self.assertLessEqual(metrics(cmds)['max_stitch_mm'],2.5+1e-8)
        self.assertLessEqual(metrics(cmds)['JUMP'],3)

    def test_hole_intervals(self):
        self.assertEqual(scanline_intervals(7,RECT,[HOLE]),[(0.,12.),(23.,35.)])
        self.assertFalse(point_inside((17,8),RECT,[HOLE]))
        self.assertTrue(point_inside((3,8),RECT,[HOLE]))

    def test_no_stitches_cross_hole(self):
        cmds=polygon_tatami(RECT,[HOLE])
        prev=None
        for c in cmds:
            if prev is not None and c.kind=='STITCH':
                for i in range(21):
                    t=i/20
                    x=prev.x+t*(c.x-prev.x)
                    y=prev.y+t*(c.y-prev.y)
                    self.assertTrue(point_inside((x,y),RECT,[HOLE]),(prev,c))
            if c.kind in ('JUMP','STITCH'):
                prev=c
        self.assertGreater(metrics(cmds)['JUMP'],2)

    def test_concave_shape_no_outside_stitches(self):
        cmds=polygon_tatami(L_SHAPE)
        prev=None
        for c in cmds:
            if prev and c.kind=='STITCH':
                for i in range(11):
                    t=i/10
                    self.assertTrue(point_inside((prev.x+t*(c.x-prev.x),
                                                   prev.y+t*(c.y-prev.y)),L_SHAPE))
            if c.kind in ('JUMP','STITCH'): prev=c

    def test_nominal_coverage(self):
        cmds=polygon_tatami(RECT,spacing=0.35)
        report=coverage_report(cmds,RECT,sample_step=0.7,thread_width=0.55)
        self.assertGreater(report['fraction'],0.75)

    def test_inset(self):
        self.assertEqual(scanline_intervals(7,RECT,[HOLE],edge_inset=0.2),
                         [(0.2,11.8),(23.2,34.8)])

    def test_invalid(self):
        with self.assertRaises(ValueError): polygon_tatami([(0,0),(1,1),(2,2)])
        with self.assertRaises(ValueError): polygon_tatami(RECT,spacing=0)
        with self.assertRaises(ValueError): polygon_tatami(RECT,edge_inset=-1)


if __name__=='__main__':
    unittest.main()
