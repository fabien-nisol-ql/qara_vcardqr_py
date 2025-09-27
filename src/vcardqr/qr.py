from __future__ import annotations
from typing import Optional
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw

def generate_qr_with_logo(
    payload: str,
    logo_path: Optional[str],
    out_path: str,
    *,
    box_size: int = 10,
    border: int = 4,
    logo_scale: float = 0.22,
    badge_rounding: int = 16,
    badge_padding_px: int = 12
) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        qr_w, qr_h = img.size
        target_w = int(qr_w * logo_scale)
        ratio = target_w / float(logo.width)
        target_h = int(logo.height * ratio)
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
    out = Image.new("RGB", img.size, (255, 255, 255))
    out.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
    out.save(out_path, format="PNG")
