import unittest,tempfile,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integrations/polyv'))
import bridge


class StatusTests(unittest.TestCase):
    def test_windows_replace_denial_never_crashes_caption_receiver(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(bridge,'STATUS',Path(folder)/'status.json'),patch.object(bridge,'CURRENT',{}),patch.object(bridge.time,'sleep'):
            with patch.object(Path,'replace',side_effect=PermissionError('locked')) as replace:
                self.assertFalse(bridge.write_status(received_count=8))
                self.assertEqual(replace.call_count,4)
            self.assertTrue(bridge.write_status(state='receiving'))
            self.assertEqual(json.loads(bridge.STATUS.read_text())['received_count'],8)

    def test_status_io_failure_is_nonfatal(self):
        with patch.object(bridge,'CURRENT',{}),patch.object(Path,'write_text',side_effect=OSError('disk error')):
            self.assertFalse(bridge.write_status(state='error'))
