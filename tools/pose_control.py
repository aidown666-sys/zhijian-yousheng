"""Experimental geometric pose controls; no SMPL-X mesh/model files are used.

Rest offsets below are hand-authored approximate proportions, not a calibrated
SMPL-X skeleton. Controls require visual and sign-language review before use.
"""
import numpy as np

PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]
OFFSETS = np.array([[0,0,0],[.09,-.09,0],[-.09,-.09,0],[0,.12,0],
    [0,-.40,0],[0,-.40,0],[0,.12,0],[0,-.40,0],[0,-.40,0],[0,.12,0],
    [0,-.03,.10],[0,-.03,.10],[0,.15,0],[.08,.08,0],[-.08,.08,0],
    [0,.15,0],[.12,0,0],[-.12,0,0],[.28,0,0],[-.28,0,0],[.25,0,0],[-.25,0,0]], dtype=float)

def rotation6d(values):
    values = np.asarray(values).reshape(-1, 6)
    first = values[:, :3]
    norm = np.linalg.norm(first, axis=-1, keepdims=True)
    first = first / np.maximum(norm, 1e-8)
    second = values[:, 3:] - np.sum(first * values[:, 3:], axis=-1, keepdims=True) * first
    second_norm = np.linalg.norm(second, axis=-1, keepdims=True)
    second = second / np.maximum(second_norm, 1e-8)
    result = np.stack([first, second, np.cross(first, second)], axis=-2)
    result[(norm[:,0] < 1e-8) | (second_norm[:,0] < 1e-8)] = np.eye(3)
    return result


def joints(body, left, right):
    matrices = rotation6d(body[:126])
    # Follow upstream visualization: keep unpredicted lower-body/spine joints neutral.
    matrices[:11] = np.eye(3)
    positions = np.zeros((22,3))
    rotations = np.repeat(np.eye(3)[None],22,axis=0)
    for index in range(1,22):
        parent = PARENTS[index]
        positions[index] = positions[parent] + rotations[parent] @ OFFSETS[index]
        rotations[index] = rotations[parent] @ matrices[index-1]
    face_center = positions[15] + [0,.015,.07]
    points = np.array([face_center,positions[12],positions[17],positions[19],positions[21],
                       positions[16],positions[18],positions[20],positions[2],positions[5],positions[8],
                       positions[1],positions[4],positions[7],face_center+[-.035,.02,0],
                       face_center+[.035,.02,0],face_center+[-.07,0,0],face_center+[.07,0,0]])
    hands = []
    for wrist, features, side in [(20,left,1),(21,right,-1)]:
        finger_rotations = rotation6d(features[:90]).reshape(5,3,3,3)
        hand = [positions[wrist].copy()]
        # Stored local finger order: index, middle, pinky, ring, thumb.
        for finger, spread in [(4,-.035),(0,-.02),(1,0),(3,.02),(2,.035)]:
            pos = positions[wrist] + rotations[wrist] @ np.array([side*.025,spread,0])
            rotation = rotations[wrist].copy()
            for joint, length in enumerate([.036,.026,.020]):
                hand.append(pos.copy())
                rotation = rotation @ finger_rotations[finger,joint]
                pos = pos + rotation @ np.array([side*length,0,0])
            hand.append(pos.copy())
        hands.append(np.array(hand))
    return points, hands

