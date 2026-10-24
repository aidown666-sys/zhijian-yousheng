import base64,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import live_server


class BackgroundTests(unittest.TestCase):
    def test_upload_fit_remove_and_decoded_image(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(live_server,'ROOT',Path(folder)):
            (Path(folder)/'runtime').mkdir()
            image=io.BytesIO();Image.new('RGB',(32,16),'blue').save(image,'PNG')
            result=live_server.save_background({'image':'data:image/png;base64,'+base64.b64encode(image.getvalue()).decode(),'fit':'cover'})
            self.assertTrue(result['enabled'])
            with Image.open(Path(folder)/'runtime/background.jpg') as saved:self.assertEqual(saved.size,(32,16))
            self.assertEqual(live_server.save_background({'fit':'contain'})['fit'],'contain')
            self.assertFalse(live_server.save_background({'image':None})['enabled'])
    def test_invalid_background_rejected(self):
        with self.assertRaises(ValueError):live_server.save_background({'image':'data:image/svg+xml;base64,AAAA'})
        with self.assertRaises(ValueError):live_server.save_background({'fit':'url(x)'})
