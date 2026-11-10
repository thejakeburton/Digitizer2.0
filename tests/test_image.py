import tempfile
import unittest
from pathlib import Path

class ImagePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import PIL, cv2, numpy
        except ImportError:
            raise unittest.SkipTest("Image dependencies are not installed")

    def _save(self, img):
        tmp=tempfile.TemporaryDirectory()
        path=Path(tmp.name)/"test.png"
        img.save(path)
        self.addCleanup(tmp.cleanup)
        return path

    def test_two_colors_and_layer_order(self):
        from PIL import Image, ImageDraw
        from digitizer.image import image_regions
        from digitizer.layers import plan_layers
        img=Image.new("RGB",(80,50),"black")
        ImageDraw.Draw(img).rectangle((15,10,60,39),fill=(255,210,0))
        regions=image_regions(self._save(img),width_mm=40)
        self.assertEqual([r.color for r in regions],["#000000","#ffd200"])
        cmds,colors=plan_layers(regions)
        self.assertEqual(colors,["#000000","#ffd200"])
        self.assertEqual(sum(c.kind=="COLOR_CHANGE" for c in cmds),1)

    def test_hole_extraction(self):
        from PIL import Image,ImageDraw
        from digitizer.image import image_regions
        img=Image.new("RGB",(100,100),"white")
        d=ImageDraw.Draw(img)
        d.rectangle((12,12,87,87),fill="black")
        d.rectangle((40,40,60,60),fill="white")
        regions=image_regions(self._save(img),width_mm=50)
        black=[r for r in regions if r.color=="#000000"]
        self.assertEqual(len(black),1)
        self.assertEqual(len(black[0].holes),1)


    def test_antialias_cleanup_integrates_with_regions(self):
        from PIL import Image
        from digitizer.image import image_regions
        img=Image.new("RGB",(120,60),(0,0,0))
        for x in range(60,120):
            for y in range(60):
                img.putpixel((x,y),(240,190,0))
        for x,t in ((58,0.25),(59,0.5),(60,0.75)):
            color=tuple(round(c*t) for c in (240,190,0))
            for y in range(60):
                img.putpixel((x,y),color)
        path=self._save(img)
        with self.assertRaisesRegex(ValueError,"exact colors"):
            image_regions(path,max_colors=2)
        regions=image_regions(path,max_colors=2,antialias_cleanup=True)
        self.assertEqual(set(r.color for r in regions),{"#000000","#f0be00"})

    def test_antialias_not_silently_quantized(self):
        from PIL import Image
        from digitizer.image import image_regions
        img=Image.new("RGB",(20,20),"white")
        for x in range(20):
            for y in range(20):
                img.putpixel((x,y),(x*12,y*12,10))
        with self.assertRaisesRegex(ValueError,"exact colors"):
            image_regions(self._save(img))

if __name__=="__main__":
    unittest.main()
