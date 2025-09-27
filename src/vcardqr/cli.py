from __future__ import annotations
import argparse
import sys
import os
import re
from typing import Dict, Any, List, Optional, NoReturn

import yaml

from .vcard import build_vcard
from .qr import generate_qr_with_logo
from .decode import decode_qr_from_file


def parse_kv_pairs(pairs: list[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs or []:
        if ":" not in p:
            raise argparse.ArgumentTypeError(f"Expected KEY:VALUE, got '{p}'")
        k, v = p.split(":", 1)
        out[k].strip() if (k := k.strip()) else k
        out[k] = v.strip()
    return out


def load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("YAML root must be a mapping/object.")
            return data
    except FileNotFoundError:
        raise SystemExit(f"Error: YAML file not found: {path}")
    except yaml.YAMLError as e:
        raise SystemExit(f"Error: Failed to parse YAML '{path}': {e}")


def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None


def fail(msg: str, code: int = 2) -> NoReturn:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


_slug_rx = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = _slug_rx.sub("_", name)
    return name or "output"


def _build_vcard_alias_context(vcard_inputs: Dict[str, Any]) -> Dict[str, Any]:
    given = vcard_inputs.get("given_name") or ""
    family = vcard_inputs.get("family_name") or ""
    adr = vcard_inputs.get("adr") or {}
    emails = vcard_inputs.get("emails") or []
    tels = vcard_inputs.get("tels") or {}

    primary_email = emails[0] if isinstance(emails, list) and emails else ""

    ctx = {
        "given_name": given,
        "family_name": family,
        "additional_names": vcard_inputs.get("additional_names") or "",
        "honorific_prefixes": vcard_inputs.get("honorific_prefixes") or "",
        "honorific_suffixes": vcard_inputs.get("honorific_suffixes") or "",
        "formatted_name": vcard_inputs.get("formatted_name") or vcard_inputs.get("fn") or f"{given} {family}".strip(),
        "org": vcard_inputs.get("org") or "",
        "title": vcard_inputs.get("title") or "",
        "email": primary_email,
        "url": vcard_inputs.get("url") or "",
        "note": vcard_inputs.get("note") or "",
        "po_box": adr.get("po_box", ""),
        "extended": adr.get("extended", ""),
        "street": adr.get("street", ""),
        "locality": adr.get("locality", ""),
        "region": adr.get("region", ""),
        "postal_code": adr.get("postal_code", ""),
        "country": adr.get("country", ""),
        "cell": tels.get("cell", ""),
        "work": tels.get("work", ""),
        "home": tels.get("home", ""),
    }
    ctx.update({
        "firstName": given,
        "lastName": family,
        "FN": ctx["formatted_name"],
        "streetAddress": ctx["street"],
        "city": ctx["locality"],
        "state": ctx["region"],
        "zip": ctx["postal_code"],
        "countryName": ctx["country"],
        "mobile": ctx["cell"],
        "phone": ctx["work"] or ctx["cell"] or ctx["home"],
    })
    return ctx


def _deep_get(root: Any, path: str) -> Any:
    cur = root
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return ""
    return cur if isinstance(cur, (str, int, float, bool)) else ""


_placeholder_rx = re.compile(r"\{([^{}]+)\}")


def _render_pattern_with_yaml(pattern: str, yaml_root: Dict[str, Any], vcard_aliases: Dict[str, Any]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        if "." in key:
            val = _deep_get(yaml_root, key)
            if val != "":
                return str(val)
        if key in vcard_aliases:
            return str(vcard_aliases[key])
        if isinstance(yaml_root.get(key, None), (str, int, float, bool)):
            return str(yaml_root[key])
        return ""
    return _placeholder_rx.sub(repl, pattern)


def _resolve_output_path(
        explicit_out: Optional[str],
        out_pattern: Optional[str],
        vcard_ctx_flat: Dict[str, Any],
        yaml_root: Dict[str, Any],
) -> str:
    if explicit_out:
        path = explicit_out
    elif out_pattern:
        rendered = _render_pattern_with_yaml(out_pattern, yaml_root, vcard_ctx_flat)
        dir_part, base = os.path.split(rendered)
        base = _sanitize_filename(base or "output")
        if not os.path.splitext(base)[1]:
            base += ".png"
        path = os.path.join(dir_part or ".", base)
    else:
        fail("Missing output destination. Provide --out or --out-pattern, or set qr.out / qr.out_pattern in YAML.")
    root, ext = os.path.splitext(path)
    if not ext:
        path = f"{path}.png"
    return path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a vCard (RFC6350) QR code with an optional centered logo, or parse a QR image."
    )

    # Mutually exclusive action: parse vs generate (default)
    act = ap.add_mutually_exclusive_group()
    act.add_argument("--parse", metavar="FILE", help="Parse QR from image FILE and print payload(s) to stdout.")

    # YAML config (for generate mode)
    ap.add_argument("--yaml", dest="yaml_file", help="YAML file with vCard + QR config")

    # vCard fields (generate mode)
    ap.add_argument("--given-name")
    ap.add_argument("--family-name")
    ap.add_argument("--fn")
    ap.add_argument("--additional-names")
    ap.add_argument("--honorific-prefixes")
    ap.add_argument("--honorific-suffixes")
    ap.add_argument("--org")
    ap.add_argument("--title")
    ap.add_argument("--email", action="append")
    ap.add_argument("--tel", action="append", default=[])
    ap.add_argument("--adr", action="append", default=[])
    ap.add_argument("--url")
    ap.add_argument("--note")

    # QR / output (generate mode)
    ap.add_argument("--logo")
    ap.add_argument("--out")
    ap.add_argument("--out-pattern")
    ap.add_argument("--box-size", type=int)
    ap.add_argument("--border", type=int)
    ap.add_argument("--logo-scale", type=float)
    ap.add_argument("--badge-rounding", type=int)
    ap.add_argument("--badge-padding", type=int)
    ap.add_argument("--size-cm", type=float)
    ap.add_argument("--size-px", type=int)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--no-create-dirs", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")

    # Show help if no args
    if len(sys.argv) == 1:
        ap.print_help(sys.stderr)
        sys.exit(1)

    args = ap.parse_args()

    # -------------------------
    # PARSE MODE
    # -------------------------
    if args.parse:
        try:
            payloads = decode_qr_from_file(args.parse)
        except FileNotFoundError:
            fail(f"Image not found: {args.parse}")
        except Exception as e:
            fail(f"Failed to decode QR from '{args.parse}': {e}")
        if not payloads:
            # No stdout output; signal with non-zero exit to be script-friendly
            print("No QR codes found.", file=sys.stderr)
            sys.exit(3)
        # Print payloads line-by-line to stdout (no extra logs)
        for p in payloads:
            print(p)
        # Optional confirmation to stderr
        print(f"✅ Parsed {len(payloads)} QR payload(s) from {args.parse}", file=sys.stderr)
        return

    # -------------------------
    # GENERATE MODE
    # -------------------------

    # Load YAML if provided
    y: Dict[str, Any] = {}
    if args.yaml_file:
        y = load_yaml(args.yaml_file)

    y_v: Dict[str, Any] = y.get("vcard") or {}
    y_qr: Dict[str, Any] = y.get("qr") or {}

    given_name = _coalesce(args.given_name, y_v.get("given_name"))
    family_name = _coalesce(args.family_name, y_v.get("family_name"))
    fn = _coalesce(args.fn, y_v.get("fn"))
    additional_names = _coalesce(args.additional_names, y_v.get("additional_names"))
    honorific_prefixes = _coalesce(args.honorific_prefixes, y_v.get("honorific_prefixes"))
    honorific_suffixes = _coalesce(args.honorific_suffixes, y_v.get("honorific_suffixes"))
    org = _coalesce(args.org, y_v.get("org"))
    title = _coalesce(args.title, y_v.get("title"))
    emails: Optional[List[str]] = _coalesce(args.email, y_v.get("emails"))

    cli_tels = parse_kv_pairs(args.tel)
    yaml_tels = y_v.get("tels") or {}
    if not isinstance(yaml_tels, dict):
        fail("YAML key 'tels' must be a mapping/dict.")
    tels = {**yaml_tels, **cli_tels} or None

    cli_adr = parse_kv_pairs(args.adr)
    yaml_adr = y_v.get("adr") or {}
    if not isinstance(yaml_adr, dict):
        fail("YAML key 'adr' must be a mapping/dict.")
    adr = {**yaml_adr, **cli_adr} or None

    url = _coalesce(args.url, y_v.get("url"))
    note = _coalesce(args.note, y_v.get("note"))

    vcard_input_map: Dict[str, Any] = {
        "given_name": given_name,
        "family_name": family_name,
        "additional_names": additional_names,
        "honorific_prefixes": honorific_prefixes,
        "honorific_suffixes": honorific_suffixes,
        "formatted_name": fn,
        "fn": fn,
        "org": org,
        "title": title,
        "emails": emails,
        "tels": tels or {},
        "adr": adr or {},
        "url": url,
        "note": note,
    }
    vcard_aliases = _build_vcard_alias_context(vcard_input_map)

    out_path = _resolve_output_path(
        explicit_out=_coalesce(args.out, y_qr.get("out")),
        out_pattern=_coalesce(args.out_pattern, y_qr.get("out_pattern")),
        vcard_ctx_flat=vcard_aliases,
        yaml_root={"vcard": y_v, "qr": y_qr, **y},
    )

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not args.no_create_dirs:
        os.makedirs(out_dir, exist_ok=True)

    logo = _coalesce(args.logo, y_qr.get("logo"))
    if logo and not os.path.isfile(logo):
        print(f"Warning: logo file not found: {logo} — continuing without logo.", file=sys.stderr)
        logo = None

    box_size = int(_coalesce(args.box_size, y_qr.get("box_size", 12)))
    border = int(_coalesce(args.border, y_qr.get("border", 4)))
    logo_scale = float(_coalesce(args.logo_scale, y_qr.get("logo_scale", 0.22)))
    badge_rounding = int(_coalesce(args.badge_rounding, y_qr.get("badge_rounding", 16)))
    badge_padding = int(_coalesce(args.badge_padding, y_qr.get("badge_padding", 12)))

    size_px = _coalesce(args.size_px, y_qr.get("size_px"))
    size_cm = float(_coalesce(args.size_cm, y_qr.get("size_cm", 3.0)))
    dpi = int(_coalesce(args.dpi, y_qr.get("dpi", args.dpi)))

    missing = [k for k, v in {"given_name": given_name, "family_name": family_name}.items() if not v]
    if missing:
        fail("Missing required fields: " + ", ".join(missing))

    try:
        vcard = build_vcard(
            given_name=given_name,
            family_name=family_name,
            additional_names=additional_names,
            honorific_prefixes=honorific_prefixes,
            honorific_suffixes=honorific_suffixes,
            formatted_name=fn,
            org=org,
            title=title,
            emails=emails,
            tels=tels,
            adr=adr,
            url=url,
            note=note,
        )
    except Exception as e:
        fail(f"Failed to build vCard: {e}")

    try:
        if args.verbose:
            print(f"Writing QR to: {out_path}", file=sys.stderr)
        generate_qr_with_logo(
            vcard,
            logo,
            out_path,
            box_size=box_size,
            border=border,
            logo_scale=logo_scale,
            badge_rounding=badge_rounding,
            badge_padding_px=badge_padding,
            size_px=int(size_px) if size_px is not None else None,
            size_cm=float(size_cm),
            dpi=int(dpi),
        )
        print(f"✅ QR code generated: {out_path}", file=sys.stderr)
    except Exception as e:
        fail(f"Failed to generate QR: {e}")


if __name__ == "__main__":
    main()
