import unittest
import numpy as np
from digitizer.palette import recover_flat_palette


class PaletteRecoveryTests(unittest.TestCase):
    def test_antialias_fringes_collapse_to_intended_colors(self):
        image=np.zeros((60,120,3),dtype=np.uint8)
        image[:,60:]=[240,190,0]
        for x,t in ((58,0.25),(59,0.5),(60,0.75)):
            image[:,x]=np.rint(np.array([240,190,0])*t).astype(np.uint8)
        clean,report=recover_flat_palette(image)
        self.assertEqual(report["output_colors"],2)
        self.assertEqual(report["unexplained_pixels"],0)
        self.assertGreater(report["changed_pixels"],0)
        self.assertEqual(len(np.unique(clean.reshape(-1,3),axis=0)),2)

    def test_preserve_small_flat_color_detail(self):
        image=np.zeros((100,100,3),dtype=np.uint8)
        image[20:80,20:80]=[200,20,10]
        image[35:40,35:40]=[10,160,230]
        for x,t in ((18,0.25),(19,0.5),(20,0.75)):
            image[20:80,x]=np.rint(np.array([200,20,10])*t).astype(np.uint8)
        clean,report=recover_flat_palette(image,max_colors=3)
        self.assertEqual(report["output_colors"],3)
        np.testing.assert_array_equal(clean[36,36],[10,160,230])

    def test_gradient_rejected(self):
        image=np.empty((40,40,3),dtype=np.uint8)
        for y in range(40):
            for x in range(40):
                image[y,x]=[x*6,y*6,(x+y)*3]
        with self.assertRaisesRegex(ValueError,"reliable flat-color palette"):
            recover_flat_palette(image)

    def test_unexplained_color_rejected_not_erased(self):
        image=np.zeros((60,60,3),dtype=np.uint8)
        image[10:50,10:50]=[240,240,0]
        image[4:6,4:6]=[20,160,200]  # meaningful 2x2; no 3x3 core
        image[5:55,8]=[120,120,0]  # intermediate antialias shade
        with self.assertRaisesRegex(ValueError,"refused|unexplained"):
            recover_flat_palette(image,max_colors=2)

    def test_exact_palette_no_op(self):
        image=np.zeros((20,20,3),dtype=np.uint8)
        image[10:]=[255,0,0]
        clean,report=recover_flat_palette(image)
        np.testing.assert_array_equal(clean,image)
        self.assertEqual(report["changed_pixels"],0)


if __name__=="__main__":
    unittest.main()
