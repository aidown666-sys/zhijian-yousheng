import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integrations/polyv'))
from watch_bridge import Captions,Viewer


class WatchBridgeTests(unittest.TestCase):
    def test_partial_revision_final_dedup(self):
        c=Captions()
        def msg(text,kind,**extra):return {'EVENT':'ADD','language':'Chinese','index':5,'text':text,'sliceType':kind,**extra}
        self.assertIsNone(c.accept(msg('今天我',0)))
        self.assertIsNone(c.accept(msg('去学校',1,replaceIndex=2)))
        self.assertEqual(c.accept(msg('今天去学校。',2,replaceIndex=0))['text'],'今天去学校。')
        self.assertIsNone(c.accept(msg('今天去学校。',2,replaceIndex=0)))
    def test_non_original_ignored_and_utf16_revision(self):
        c=Captions()
        self.assertIsNone(c.accept({'EVENT':'TRANSLATE','language':'English','text':'hello','sliceType':2,'index':1}))
        c.accept({'EVENT':'ADD','language':'Chinese','text':'😀你','sliceType':0,'index':2})
        self.assertEqual(c.accept({'EVENT':'ADD','language':'Chinese','text':'好','replaceIndex':2,'sliceType':2,'index':2})['text'],'😀好')
    def test_restricted_destination_not_accepted(self):
        with self.assertRaises(ValueError):Viewer('https://example.com/watch/1')


if __name__=='__main__':unittest.main()
