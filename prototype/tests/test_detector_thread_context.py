import unittest
from types import SimpleNamespace

try:
    import torch
except ImportError:
    torch = None

from prototype.stone_detector import StoneDetector


@unittest.skipIf(torch is None, 'Requires detector/tracking torch environment')
class ThreadContextTest(unittest.TestCase):
    def test_upstream_exception_restores_callers_thread_setting(self):
        original = torch.get_num_threads()
        detector = object.__new__(StoneDetector)
        detector.threads = 1
        detector.imgsz = 1280
        detector.device = 'cpu'

        def fail(*args, **kwargs):
            torch.set_num_threads(8)  # upstream CPU setup
            detector._configure_prediction_threads(None)
            self.assertEqual(torch.get_num_threads(), 1)
            raise RuntimeError('inference failed')

        detector.model = SimpleNamespace(predict=fail)
        try:
            torch.set_num_threads(4)
            with self.assertRaisesRegex(RuntimeError, 'inference failed'):
                detector.detect(None)
            self.assertEqual(torch.get_num_threads(), 4)
        finally:
            torch.set_num_threads(original)


if __name__ == '__main__':
    unittest.main()
