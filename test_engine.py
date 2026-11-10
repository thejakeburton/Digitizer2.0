import unittest
from digitizer.engine import rectangle_tatami, metrics


class TestEngine(unittest.TestCase):
    def test_bounds_and_terminator(self):
        commands = rectangle_tatami(35, 18)
        self.assertEqual(commands[-1].kind, 'END')
        self.assertTrue(all(0 <= c.x <= 35 and 0 <= c.y <= 18 for c in commands))

    def test_row_count_and_stitch_count(self):
        commands = rectangle_tatami(35, 18, spacing=0.4)
        self.assertEqual(metrics(commands)['JUMP'], 46)
        self.assertGreater(metrics(commands)['STITCH'], 500)

    def test_staggered_penetrations(self):
        commands = rectangle_tatami(35, 18)
        row0 = [c.x for c in commands if c.kind == 'STITCH' and c.y == 0]
        row1y = min(c.y for c in commands if c.kind == 'STITCH' and c.y > 0)
        row1 = [c.x for c in commands if c.kind == 'STITCH' and c.y == row1y]
        self.assertNotEqual(sorted(row0), sorted(row1))

    def test_reject_invalid(self):
        with self.assertRaises(ValueError):
            rectangle_tatami(spacing=0)


if __name__ == '__main__':
    unittest.main()
