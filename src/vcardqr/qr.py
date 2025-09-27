from __future__ import annotations
from typing import Optional
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw


def _validate_params(box_size: int, border: int, logo_scale: float) -> None:
    if box_size <= 0:
        raise ValueError("box_size must be > 0.")
    if border < 1:
        raise ValueError("border must be >= 1 (recommend 4).")
    if not (0.0 <= logo_scale <= 0.35):
        raise ValueError("logo_scale must be between 0.0 and 0.35.")


def _cm_to_px(cm: float, dpi: int) -> int:
    # inches = cm / 2.54; px = inches * dpi
    return max(1, int(round((cm / 2.54) * dpi)))


def generate_qr_with_logo(
        payload: str,
        logo_path: Optional[str],
        out_path: str,
        *,
        box_size: int = 10,
        border: int = 4,
        logo_scale: float = 0.22,
        badge_rounding: int = 16,
        badge_padding_px: int = 12,
        # final output sizing
        size_px: Optional[int] = None,
        size_cm: float = 3.0,
        dpi: int = 300,
) -> None:
    """
    Generate QR code with optional centered logo/badge.
    The base QR is created at (modules * box_size) then resized to a final square:
      - If size_px is provided: final size is size_px x size_px
      - Else: final size is size_cm converted via dpi (default 3 cm at 300 dpi)
    """
    if not out_path:
        raise ValueError("Output path is empty. Provide --out or qr.out in YAML.")
    _validate_params(box_size, border, logo_scale)

    # Build QR at base resolution
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    # Optional logo
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")
        except FileNotFoundError:
            logo = None
        if logo:
            qr_w, qr_h = img.size
            target_w = max(1, int(qr_w * logo_scale))
            ratio = target_w / float(logo.width)
            target_h = max(1, int(logo.height * ratio))
            logo = logo.resize((target_w, target_h), Image.LANCZOS)

            badge_w = target_w + 2 * badge_padding_px
            badge_h = target_h + 2 * badge_padding_px
            badge = Image.new("RGBA", (badge_w, badge_h), (255, 255, 255, 0))
            draw = ImageDraw.Draw(badge)
            rect = [0, 0, badge_w, badge_h]
            draw.rounded_rectangle(rect, radius=badge_rounding, fill=(255, 255, 255, 255))
            draw.rounded_rectangle(rect, radius=badge_rounding, outline=(0, 0, 0, 40), width=2)
            badge.paste(logo, (badge_padding_px, badge_padding_px), mask=logo)

            bx = (qr_w - badge_w) // 2
            by = (qr_h - badge_h) // 2
            img.alpha_composite(badge, (bx, by))

    # Ensure parent dir exists
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Convert to RGB before saving/resizing
    out_rgb = Image.new("RGB", img.size, (255, 255, 255))
    out_rgb.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)

    # Determine final size (square)
    final_px = int(size_px) if size_px is not None else _cm_to_px(float(size_cm), int(dpi))
    if final_px <= 0:
        raise ValueError("Final size must be positive (from size_px or size_cm/dpi).")

    # Resize only if needed
    if out_rgb.size[0] != final_px:
        out_rgb = out_rgb.resize((final_px, final_px), Image.LANCZOS)

    # Save
    out_rgb.save(out_path, format="PNG")
