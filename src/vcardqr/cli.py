# simplified version with YAML support
from __future__ import annotations
import argparse, yaml
from typing import Dict, Any, List, Optional
from .vcard import build_vcard
from .qr import generate_qr_with_logo

def parse_kv_pairs(pairs: list[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs or []:
        if ":" not in p: raise argparse.ArgumentTypeError(f"Expected KEY:VALUE, got '{p}'")
        k, v = p.split(":", 1); out[k] = v
    return out

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", [], {}): return v
    return None

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", dest="yaml_file")
    ap.add_argument("--given-name"); ap.add_argument("--family-name")
    ap.add_argument("--fn"); ap.add_argument("--additional-names")
    ap.add_argument("--honorific-prefixes"); ap.add_argument("--honorific-suffixes")
    ap.add_argument("--org"); ap.add_argument("--title")
    ap.add_argument("--email", action="append")
    ap.add_argument("--tel", action="append", default=[])
    ap.add_argument("--adr", action="append", default=[])
    ap.add_argument("--url"); ap.add_argument("--note")
    ap.add_argument("--logo"); ap.add_argument("--out")
    ap.add_argument("--box-size", type=int); ap.add_argument("--border", type=int)
    ap.add_argument("--logo-scale", type=float)
    ap.add_argument("--badge-rounding", type=int); ap.add_argument("--badge-padding", type=int)
    args = ap.parse_args()
    y = load_yaml(args.yaml_file) if args.yaml_file else {}
    y_v = y.get("vcard") or {}; y_qr = y.get("qr") or {}
    given_name = _coalesce(args.given_name, y_v.get("given_name"))
    family_name = _coalesce(args.family_name, y_v.get("family_name"))
    fn = _coalesce(args.fn, y_v.get("fn"))
    emails = _coalesce(args.email, y_v.get("emails"))
    tels = {**(y_v.get("tels") or {}), **parse_kv_pairs(args.tel)} or None
    adr = {**(y_v.get("adr") or {}), **parse_kv_pairs(args.adr)} or None
    out_path = _coalesce(args.out, y_qr.get("out"))
    logo = _coalesce(args.logo, y_qr.get("logo"))
    box_size = _coalesce(args.box_size, y_qr.get("box_size", 12))
    border = _coalesce(args.border, y_qr.get("border", 4))
    logo_scale = _coalesce(args.logo_scale, y_qr.get("logo_scale", 0.22))
    badge_rounding = _coalesce(args.badge_rounding, y_qr.get("badge_rounding", 16))
    badge_padding = _coalesce(args.badge_padding, y_qr.get("badge_padding", 12))
    vcard = build_vcard(
        given_name=given_name, family_name=family_name,
        formatted_name=fn, org=_coalesce(args.org, y_v.get("org")),
        title=_coalesce(args.title, y_v.get("title")),
        emails=emails, tels=tels, adr=adr,
        url=_coalesce(args.url, y_v.get("url")),
        note=_coalesce(args.note, y_v.get("note")),
    )
    generate_qr_with_logo(vcard, logo, out_path,
                          box_size=int(box_size), border=int(border),
                          logo_scale=float(logo_scale),
                          badge_rounding=int(badge_rounding),
                          badge_padding_px=int(badge_padding))
if __name__ == "__main__":
    main()
