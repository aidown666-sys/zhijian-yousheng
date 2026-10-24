import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pose_control import rotation6d, joints


class GeometryTests(unittest.TestCase):
    def test_identity_and_degenerate_rotations(self):
        result=rotation6d([[1,0,0,0,1,0],[0,0,0,0,0,0]])
        np.testing.assert_allclose(result,np.repeat(np.eye(3)[None],2,axis=0))

    def test_rotation_is_orthonormal(self):
        values=np.random.default_rng(42).normal(size=(64,6))
        rotation=rotation6d(values)
        np.testing.assert_allclose(rotation@rotation.transpose(0,2,1),np.broadcast_to(np.eye(3),(64,3,3)),atol=1e-10)
        np.testing.assert_allclose(np.linalg.det(rotation),1,atol=1e-10)

    def test_body_and_hand_topology(self):
        identity=np.array([1,0,0,0,1,0])
        body,hands=joints(np.tile(identity,21),np.tile(identity,16),np.tile(identity,16))
        self.assertEqual(body.shape,(18,3))
        self.assertEqual(hands[0].shape,(21,3))
        self.assertTrue(np.isfinite(body).all())
        np.testing.assert_allclose(hands[0][0],body[7])
        np.testing.assert_allclose(hands[1][0],body[4])


if __name__=='__main__':
    unittest.main()
