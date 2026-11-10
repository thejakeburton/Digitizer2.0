import unittest
from digitizer.layers import Region, plan_layers
from digitizer.engine import metrics

RECT=((0,0),(20,0),(20,10),(0,10))
SMALL=((5,2),(15,2),(15,8),(5,8))

class LayerTests(unittest.TestCase):
    def test_background_detail_background_preserves_order(self):
        regions=[Region("#000000",RECT),Region("#ffcc00",SMALL),Region("#000000",SMALL)]
        commands,colors=plan_layers(regions)
        self.assertEqual(colors,["#000000","#ffcc00","#000000"])
        self.assertEqual(metrics(commands)["COLOR_CHANGE"],2)
        self.assertEqual(commands[-1].kind,"END")

    def test_adjacent_same_color_reuses_thread(self):
        cmds,colors=plan_layers([Region("#ffffff",RECT),Region("#FFFFFF",SMALL)])
        self.assertEqual(colors,["#ffffff"])
        self.assertEqual(metrics(cmds)["COLOR_CHANGE"],0)
        self.assertEqual(metrics(cmds)["JUMP"],2)

    def test_invalid_region_rejected(self):
        with self.assertRaises(ValueError): plan_layers([])
        with self.assertRaises(ValueError): plan_layers([Region("blue",RECT)])
        with self.assertRaises(ValueError): plan_layers([Region("#ffffff",RECT,role="satin")])

if __name__=="__main__":
    unittest.main()
