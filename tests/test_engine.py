import unittest
from math import hypot
from digitizer.engine import Command, rectangle_tatami, metrics


class TestEngine(unittest.TestCase):
    def test_bounds_and_terminator(self):
        commands = rectangle_tatami(35, 18)
        self.assertEqual(commands[-1].kind, 'END')
        self.assertTrue(all(0 <= c.x <= 35 and 0 <= c.y <= 18 for c in commands))

    def test_serpentine_reduces_jumps(self):
        commands = rectangle_tatami(35, 18, underlay=False)
        self.assertEqual(metrics(commands)['JUMP'], 1)
        self.assertGreater(metrics(commands)['STITCH'], 500)
        self.assertLessEqual(metrics(commands)['max_stitch_mm'], 2.5 + 1e-8)

    def test_underlay_adds_one_reposition(self):
        bare = rectangle_tatami(35, 18, underlay=False)
        supported = rectangle_tatami(35, 18, underlay=True)
        self.assertEqual(metrics(supported)['JUMP'], 2)
        self.assertGreater(metrics(supported)['STITCH'], metrics(bare)['STITCH'])
        self.assertLessEqual(metrics(supported)['max_stitch_mm'], 2.5 + 1e-8)

    def test_fill_row_coverage_and_stagger(self):
        commands = rectangle_tatami(35, 18, spacing=0.4, underlay=False)
        rows = {}
        for c in commands:
            if c.kind == 'STITCH' and c.y not in rows:
                rows[c.y] = []
            if c.kind == 'STITCH':
                rows[c.y].append(c.x)
        ys = sorted(rows)
        self.assertEqual(len(ys), 46)
        self.assertTrue(all(b - a <= 0.400001 for a, b in zip(ys, ys[1:])))
        self.assertTrue(all(min(rows[y]) <= 1e-8 and max(rows[y]) >= 35 - 1e-8 for y in ys[1:]))
        self.assertNotEqual(sorted(rows[ys[0]]), sorted(rows[ys[1]]))

    def test_no_diagonal_row_travel(self):
        commands = rectangle_tatami(35, 18, underlay=False)
        previous = None
        for c in commands:
            if c.kind == 'STITCH' and previous is not None:
                # Fill stitches are horizontal; row connectors are vertical.
                self.assertTrue(abs(c.x - previous.x) < 1e-8 or abs(c.y - previous.y) < 1e-8)
            if c.kind in ('STITCH', 'JUMP'):
                previous = c

    def test_reject_invalid(self):
        for kw in ({'spacing': 0}, {'width': float('nan')}, {'height': 0.1}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                rectangle_tatami(**kw)


if __name__ == '__main__':
    unittest.main()
