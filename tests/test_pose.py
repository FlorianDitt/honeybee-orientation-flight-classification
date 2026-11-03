import cv2
import numpy as np

from beeflight.pose import axial_diff, circ_diff, estimate, heading


def bee(angle, dark_front=True):
    """Gray crop with an elongated blob at `angle` (deg, image coordinates), darker on the +axis half if asked."""
    bg = np.full((96, 96), 150, np.uint8)
    img = bg.copy()
    cv2.ellipse(img, (48, 48), (15, 6), angle, 0, 360, 90, -1)
    if dark_front:
        cv2.ellipse(img, (48, 48), (15, 6), angle, -90, 90, 40, -1)  # +axis half darker
    return img, bg


def test_axis_and_darker_half():
    for angle in (0, 30, 75, 120, 160):
        img, bg = bee(angle)
        e = estimate(img, bg, 48, 48)
        assert axial_diff(e["axis_deg"], angle) < 3
        assert e["elong"] > 2
        assert circ_diff(heading(e["axis_deg"], e["darker"]), angle) < 3


def test_no_blob_far_from_the_track_point():
    img, bg = bee(0)
    assert estimate(img, bg, 5, 5) is None
    assert estimate(bg.copy(), bg, 48, 48) is None


def test_angle_helpers():
    assert axial_diff(10, 170) == 20
    assert circ_diff(350, 10) == 20
    assert heading(30, -1) == 210
