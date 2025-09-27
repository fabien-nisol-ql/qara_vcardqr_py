from __future__ import annotations
import argparse
import sys
import os
import re
from typing import Dict, Any, List, Optional, NoReturn

import yaml

# We keep heavy imports (opencv, PIL, qrcode) out of module scope for faster startup.


# ---------- Utilities ----------

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


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dicts: override takes precedence."""
    out: Dict[str, Any] = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


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


def _deep_get(root: Any, path: str) -> Any:
    """Resolve dotted path like 'vcard.given_name' or 'qr.size_px' against nested dicts."""
    cur = root
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return ""
    return cur if isinstance(cur, (str, int, float, bool)) else ""


def _render_pattern_with_yaml(pattern: str, yaml_root: Dict[str, Any], vcard_aliases: Dict[str, Any]) -> str:
    """
    Render out_pattern allowing dotted YAML paths and friendly/flat aliases.
    Aliases live in vcard_aliases (firstName/lastName/given_name/…).
    """
    placeholder_rx = re.compile(r"\{([^{}]+)\}")

    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        # dotted lookup first
        if "." in key:
            val = _deep_get(yaml_root, key)
            if val != "":
                return str(val)
        # alias lookup
        if key in vcard_aliases:
            return str(vcard_aliases[key])
        # top-level scalar last
        if isinstance(yaml_root.get(key, None), (str, int, float, bool)):
            return str(yaml_root[key])
        return ""

    return placeholder_rx.sub(repl, pattern)


def _build_vcard_alias_context(vcard_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Friendly aliases for vcard fields (firstName/lastName/etc.)."""
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
        # address
        "po_box": adr.get("po_box", ""),
        "extended": adr.get("extended", ""),
        "street": adr.get("street", ""),
        "locality": adr.get("locality", ""),
        "region": adr.get("region", ""),
        "postal_code": adr.get("postal_code", ""),
        "country": adr.get("country", ""),
        # phones
        "cell": tels.get("cell", ""),
        "work": tels.get("work", ""),
        "home": tels.get("home", ""),
    }

    # friendly aliases
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


def _resolve_output_path(
        explicit_out: Optional[str],
        out_pattern: Optional[str],
        vcard_ctx_flat: Dict[str, Any],
        yaml_root: Dict[str, Any],
        base_dir: Optional[str],
) -> str:
    """
    Decide output path:
      - If explicit_out is provided -> use it.
      - Else if out_pattern is provided -> render it.
      - Else -> error.
    Adds '.png' if no extension is present. Sanitizes only the basename.
    Resolve relative paths against `base_dir` (the YAML file's directory), unless piping to /dev/*.
    """
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
        fail("Missing output destination. Provide qr.out or qr.out_pattern in YAML, or pass --out/--out-pattern.")

    # Resolve relative paths against YAML directory (unless piping)
    if base_dir and not os.path.isabs(path) and not path.startswith("/dev/"):
        path = os.path.normpath(os.path.join(base_dir, path))

    # Ensure extension
    root, ext = os.path.splitext(path)
    if not ext:
        path = f"{path}.png"
    return path


# ---------- Main ----------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate vCard (RFC6350) QR code(s) from YAML, or parse a QR image."
    )

    # Mutually exclusive action: parse vs generate (default)
    act = ap.add_mutually_exclusive_group()
    act.add_argument("--parse", metavar="FILE", help="Parse QR from image FILE and print payload(s) to stdout.")

    # YAML file (generate mode). Supports:
    #  - Single-person YAML with top-level 'vcard' + 'qr'
    #  - Batch YAML with 'defaults' + 'persons'
    ap.add_argument("--yaml", dest="yaml_file", help="YAML file. Supports either single-person or defaults+persons.")

    # Show help if no args
    if len(sys.argv) == 1:
        ap.print_help(sys.stderr)
        sys.exit(1)

    args = ap.parse_args()

    # -------------------------
    # PARSE MODE
    # -------------------------
    if args.parse:
        # UX: warn heavy import (first time can be slow)
        print("⏳ Loading OpenCV (first time can take a while)...", file=sys.stderr, flush=True)
        try:
            # Lazy import to avoid cv2 at startup
            from .decode import decode_qr_from_file  # type: ignore
            payloads = decode_qr_from_file(args.parse)
        except FileNotFoundError:
            fail(f"Image not found: {args.parse}")
        except ImportError as e:
            # decode.py will raise an informative message about installing the extra
            fail(str(e))
        except Exception as e:
            fail(f"Failed to decode QR from '{args.parse}': {e}")

        if not payloads:
            print("No QR codes found.", file=sys.stderr)
            sys.exit(3)

        for p in payloads:
            print(p)  # stdout only payloads
        print(f"✅ Parsed {len(payloads)} QR payload(s) from {args.parse}", file=sys.stderr)
        return

    # -------------------------
    # GENERATE MODE
    # -------------------------
    if not args.yaml_file:
        fail("Missing --yaml. Provide a YAML file (single-person or defaults+persons).")

    # Lazy import generate-only stuff
    from .vcard import build_vcard  # type: ignore
    from .qr import generate_qr_with_logo  # type: ignore

    # Load YAML
    root_yaml = load_yaml(args.yaml_file)
    yaml_dir = os.path.dirname(os.path.abspath(args.yaml_file))

    persons: List[Dict[str, Any]] = []
    defaults = root_yaml.get("defaults")

    if "persons" in root_yaml:
        # Batch mode: defaults + persons
        if defaults and not isinstance(defaults, dict):
            fail("'defaults' must be a mapping/object.")
        defaults = defaults or {}
        persons_raw = root_yaml.get("persons") or []
        if not isinstance(persons_raw, list) or not persons_raw:
            fail("'persons' must be a non-empty list.")
        for entry in persons_raw:
            if not isinstance(entry, dict):
                fail("Each item in 'persons' must be a mapping/object.")
            persons.append(deep_merge(defaults, entry))
    elif "vcard" in root_yaml or "qr" in root_yaml:
        # Single-person YAML
        persons = [root_yaml]
    else:
        fail("YAML must define either top-level 'vcard'/'qr' or 'defaults' + 'persons'.")

    # Generate for each person
    for idx, merged in enumerate(persons, start=1):
        v = merged.get("vcard") or {}
        q = merged.get("qr") or {}

        given_name = v.get("given_name")
        family_name = v.get("family_name")
        if not given_name or not family_name:
            fail(f"Person {idx} missing required fields 'given_name'/'family_name'.")

        # Build vCard payload
        try:
            vcard = build_vcard(
                given_name=given_name,
                family_name=family_name,
                additional_names=v.get("additional_names"),
                honorific_prefixes=v.get("honorific_prefixes"),
                honorific_suffixes=v.get("honorific_suffixes"),
                formatted_name=v.get("fn"),
                org=v.get("org"),
                title=v.get("title"),
                emails=v.get("emails"),
                tels=v.get("tels"),
                adr=v.get("adr"),
                url=v.get("url"),
                note=v.get("note"),
            )
        except Exception as e:
            fail(f"Failed to build vCard for person {idx}: {e}")

        # Build alias context for patterns
        vcard_input_map: Dict[str, Any] = {
            "given_name": given_name,
            "family_name": family_name,
            "additional_names": v.get("additional_names"),
            "honorific_prefixes": v.get("honorific_prefixes"),
            "honorific_suffixes": v.get("honorific_suffixes"),
            "formatted_name": v.get("fn"),
            "fn": v.get("fn"),
            "org": v.get("org"),
            "title": v.get("title"),
            "emails": v.get("emails"),
            "tels": v.get("tels") or {},
            "adr": v.get("adr") or {},
            "url": v.get("url"),
            "note": v.get("note"),
        }
        v_alias = _build_vcard_alias_context(vcard_input_map)

        # Resolve output path (out wins over out_pattern)
        out_path = _resolve_output_path(
            explicit_out=q.get("out"),
            out_pattern=q.get("out_pattern"),
            vcard_ctx_flat=v_alias,
            yaml_root=merged,  # allow {vcard.*}, {qr.*}, or other keys
            base_dir=yaml_dir,
        )

        # Ensure directory
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir:
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                fail(f"Cannot create output directory '{out_dir}': {e}")

        # Resolve logo relative to YAML
        logo = q.get("logo")
        if logo and not os.path.isabs(logo):
            logo = os.path.normpath(os.path.join(yaml_dir, logo))
        if logo and not os.path.isfile(logo):
            print(f"Warning: logo file not found: {logo} — continuing without logo.", file=sys.stderr)
            logo = None

        # Generate QR
        try:
            if True:  # keep for readability; could use a --verbose flag
                print(f"Writing QR to: {out_path}", file=sys.stderr)
            generate_qr_with_logo(
                vcard,
                logo,
                out_path,
                box_size=int(q.get("box_size", 12)),
                border=int(q.get("border", 4)),
                logo_scale=float(q.get("logo_scale", 0.22)),
                badge_rounding=int(q.get("badge_rounding", 16)),
                badge_padding_px=int(q.get("badge_padding", 12)),
                size_px=int(q["size_px"]) if "size_px" in q and q["size_px"] is not None else None,
                size_cm=float(q.get("size_cm", 3.0)),
                dpi=int(q.get("dpi", 300)),
            )
            fn_disp = v_alias.get("FN") or f"{given_name} {family_name}"
            print(f"✅ Generated QR for {fn_disp} → {out_path}", file=sys.stderr)
        except Exception as e:
            fail(f"Failed to generate QR for person {idx}: {e}")


if __name__ == "__main__":
    main()
