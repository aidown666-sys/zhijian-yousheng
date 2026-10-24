import unittest
from live_server import MotionLibrary, Stream


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = MotionLibrary()

    def test_known_caption_contains_actual_hand_frames(self):
        motion = self.library.motion('他今年四岁。')
        self.assertEqual(len(motion['frames']), 54)
        self.assertEqual(len(motion['frames'][0]['hands'][0]), 21)
        self.assertNotEqual(motion['frames'][0], motion['frames'][-1])

    def test_partial_and_retries_do_not_duplicate_motion(self):
        stream = Stream(self.library)
        self.assertEqual(stream.submit({'id': '1', 'text': '他今年四岁。', 'final': False})['status'], 'partial_ignored')
        self.assertEqual(stream.submit({'id': '1', 'text': '他今年四岁。'})['status'], 'queued')
        self.assertEqual(stream.submit({'id': '1', 'text': '他今年四岁。'})['status'], 'duplicate')
        self.assertEqual(len(stream.events), 1)

    def test_unknown_keeps_caption_without_fake_gesture(self):
        stream = Stream(self.library)
        self.assertEqual(stream.submit({'text': '这是一个没有被收录的随机句子xyz'})['status'], 'unsupported')
        self.assertIsNone(stream.events[0]['motion'])

    def test_invalid_final_is_rejected(self):
        with self.assertRaises(ValueError):
            Stream(self.library).submit({'text': '你好', 'final': 'false'})

    def test_new_sentence_can_compose_real_word_motion(self):
        text='今天我去学校'
        self.assertNotIn(text,self.library.index)
        motion=self.library.motion(text)
        self.assertEqual(motion['method'],'word-concatenation')
        self.assertEqual(''.join(motion['tokens']),text)
        self.assertGreater(len(motion['frames']),5)

    def test_missing_vocabulary_does_not_silently_drop_words(self):
        with self.assertRaisesRegex(ValueError,'x.*y.*z'):
            self.library.motion('xyz')

    def test_stream_tracks_output_clients(self):
        stream=Stream(self.library)
        self.assertEqual(stream.outputs,{})

    def test_partial_preview_reports_missing_instead_of_claiming_full_translation(self):
        motion=self.library.motion('今天我去学校xyz',allow_partial=True)
        self.assertTrue(motion['partial'])
        self.assertEqual(motion['missing'],['x','y','z'])
        self.assertEqual(motion['method'],'partial-word-preview')
        self.assertIn('非完整',motion['warning'])
        self.assertGreater(len(motion['frames']),5)
        with self.assertRaises(ValueError):self.library.motion('xyz',allow_partial=True)


if __name__ == '__main__':
    unittest.main()
