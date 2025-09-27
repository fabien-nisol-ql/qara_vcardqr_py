from __future__ import annotations
from typing import List, Iterable, Set
import os

def decode_qr_from_file(path: str) -> List[str]:
    """
    Decode QR payload(s) from an image file using OpenCV's QRCodeDetector.
    Tries multiple pre-processing variants and crisp resizes to improve robustness,
    especially for QR codes with center logos.

    Returns a list of unique decoded strings. Raises FileNotFoundError if path not found.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    # Lazy imports so normal 'generate' path stays fast
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as e:
        raise ImportError(
            "OpenCV is required for --parse. Install with: pip install 'vcardqr[parse]' "
            "or: pip install opencv-python"
        ) from e

    # Read with alpha (if any), then composite on white to avoid transparency artifacts
    src = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if src is None:
        raise ValueError(f"Unable to read image: {path}")

    if len(src.shape) == 2:
        base = src  # grayscale
    elif src.shape[2] == 4:
        b, g, r, a = cv2.split(src)
        alpha = (a.astype(float) / 255.0)[..., None]
        rgb = cv2.merge([r, g, b]).astype(float)
        white = np.ones_like(rgb) * 255.0
        comp_rgb = (rgb * alpha + white * (1.0 - alpha)).astype("uint8")
        base = cv2.cvtColor(comp_rgb, cv2.COLOR_RGB2GRAY)
    else:
        base = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

    # Build candidate images: original gray + thresholded + adaptive + resized
    candidates: List["np.ndarray"] = []
    candidates.append(base)

    # Otsu threshold (global)
    try:
        _, otsu = cv2.threshold(base, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(otsu)
    except Exception:
        pass

    # Adaptive thresholds
    try:
        adap_mean = cv2.adaptiveThreshold(
            base, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 41, 5
        )
        candidates.append(adap_mean)
    except Exception:
        pass

    try:
        adap_gauss = cv2.adaptiveThreshold(
            base, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 5
        )
        candidates.append(adap_gauss)
    except Exception:
        pass

    # Slight denoise + Otsu again
    try:
        blur = cv2.GaussianBlur(base, (3, 3), 0)
        _, otsu2 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(otsu2)
    except Exception:
        pass

    # Try a few crisp upscales (helps the detector a lot on small/fuzzy QRs)
    def crisp_resize(img: "np.ndarray", scale: float) -> "np.ndarray":
        h, w = img.shape[:2]
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        # Use NEAREST to keep module edges crisp
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

    scales = [1.0, 1.25, 1.5, 2.0, 3.0]
    expanded: List["np.ndarray"] = []
    for img in candidates:
        for s in scales:
            expanded.append(crisp_resize(img, s))

    detector = cv2.QRCodeDetector()

    def try_decode(img: "np.ndarray") -> List[str]:
        # Try multi-QR first (OpenCV >= 4.5)
        try:
            retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
            if retval and decoded_info:
                return [s for s in decoded_info if isinstance(s, str) and s]
        except TypeError:
            # Some builds have different signatures; ignore and fall back
            pass
        except Exception:
            pass

        # Single QR fallback
        try:
            # Newer OpenCV returns (data, points, straight); some older only (data, points)
            out = detector.detectAndDecode(img)
            if isinstance(out, tuple):
                data = out[0]
            else:
                data = out
            return [data] if data else []
        except Exception:
            return []

    payloads: Set[str] = set()
    for variant in expanded:
        decoded = try_decode(variant)
        for p in decoded:
            # Basic sanity: ignore obviously empty results
            if p and isinstance(p, str):
                payloads.add(p)
        if payloads:
            break  # early exit on first success

    return list(payloads)
