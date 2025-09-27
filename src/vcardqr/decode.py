from __future__ import annotations
from typing import List
import os

import cv2  # OpenCV


def decode_qr_from_file(path: str) -> List[str]:
    """
    Decode QR payload(s) from an image file using OpenCV's QRCodeDetector.
    Returns a list of decoded strings. Raises FileNotFoundError if path not found.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    img = cv2.imread(path)
    if img is None:
        # File exists but couldn't be read as an image
        raise ValueError(f"Unable to read image: {path}")

    detector = cv2.QRCodeDetector()

    # Try multi-QR first (OpenCV 4.5+)
    payloads: List[str] = []
    try:
        # Newer OpenCV returns (retval, decoded_info, points, straight_qrcode)
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        if retval and decoded_info:
            payloads.extend([s for s in decoded_info if isinstance(s, str) and s])
    except TypeError:
        # Fallback: some builds have a different signature; ignore and try single
        pass
    except Exception:
        # Any unexpected error in multi-decode -> fall back to single
        pass

    if not payloads:
        # Single QR fallback
        try:
            data, points, _ = detector.detectAndDecode(img)
        except ValueError:
            # Some older versions return only (data, points)
            data, points = detector.detectAndDecode(img)  # type: ignore[misc]
        if data:
            payloads.append(data)

    return payloads
