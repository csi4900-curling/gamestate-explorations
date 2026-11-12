import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

from prototype.spin.online_checkpoint import ONLINE_FIELDS, restore, save


def predictor():
    state = {name: torch.arange(4).reshape(1,4).float() for name in ONLINE_FIELDS}
    state.update(online_ind=8, online_track_feat=[torch.ones(2),None],
                 online_track_support=[torch.zeros(2),None])
    return SimpleNamespace(model=SimpleNamespace(**state), step=8, N=1,
                           queries=torch.tensor([[[0.,1.,2.]]]))


class OnlineCheckpointTests(unittest.TestCase):
    def test_roundtrip_and_changed_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.pt'; source=predictor()
            contract={'input':'abc','torch':torch.__version__, 'shape':(1,16,1,2)}
            save(path,source,contract,8,torch.ones(1,16,1,2),torch.ones(1,16,1,dtype=torch.bool))
            target=predictor();target.model.online_ind=0
            with self.assertRaisesRegex(ValueError,'contract differs'):
                restore(path,target,{**contract,'input':'other'},'cpu')
            self.assertEqual(target.model.online_ind,0)
            offset,tracks,visible=restore(path,target,contract,'cpu')
            self.assertEqual(offset,8)
            self.assertTrue(torch.equal(tracks,torch.ones(1,16,1,2)))
            self.assertEqual(visible.dtype,torch.bool)
            self.assertTrue(torch.equal(source.queries,target.queries))

    def test_failed_save_preserves_previous_committed_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.pt'; source=predictor();contract={'input':'abc'}
            save(path,source,contract,8,torch.ones(1),torch.ones(1,dtype=torch.bool))
            before=path.read_bytes()
            with patch.object(torch,'save',side_effect=OSError('interrupted write')):
                with self.assertRaises(OSError):
                    save(path,source,contract,8,torch.zeros(1),torch.zeros(1,dtype=torch.bool))
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(restore(path,predictor(),contract,'cpu')[0],8)


if __name__=='__main__':
    unittest.main()
