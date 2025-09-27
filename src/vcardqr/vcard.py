from __future__ import annotations
from typing import Optional, Dict, List

def _escape_vcard(value: str) -> str:
    if value is None:
        return ""
    v = value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
    return v

def build_vcard(
    *,
    given_name: str,
    family_name: str,
    additional_names: Optional[str] = None,
    honorific_prefixes: Optional[str] = None,
    honorific_suffixes: Optional[str] = None,
    formatted_name: Optional[str] = None,
    org: Optional[str] = None,
    title: Optional[str] = None,
    emails: Optional[List[str]] = None,
    tels: Optional[Dict[str, str]] = None,
    adr: Optional[Dict[str, str]] = None,
    url: Optional[str] = None,
    note: Optional[str] = None
) -> str:
    fn = formatted_name or f"{given_name} {family_name}".strip()
    n_parts = [
        _escape_vcard(family_name or ""),
        _escape_vcard(given_name or ""),
        _escape_vcard(additional_names or ""),
        _escape_vcard(honorific_prefixes or ""),
        _escape_vcard(honorific_suffixes or "")
    ]
    n_value = ";".join(n_parts)
    lines = [
        "BEGIN:VCARD",
        "VERSION:4.0",
        f"N:{n_value}",
        f"FN:{_escape_vcard(fn)}",
    ]
    if org: lines.append(f"ORG:{_escape_vcard(org)}")
    if title: lines.append(f"TITLE:{_escape_vcard(title)}")
    if emails:
        for e in emails: lines.append(f"EMAIL:{_escape_vcard(e)}")
    if tels:
        for tel_type, number in tels.items():
            lines.append(f"TEL;TYPE={_escape_vcard(tel_type)}:{_escape_vcard(number)}")
    if adr:
        adr_fields = [
            _escape_vcard(adr.get("po_box", "")),
            _escape_vcard(adr.get("extended", "")),
            _escape_vcard(adr.get("street", "")),
            _escape_vcard(adr.get("locality", "")),
            _escape_vcard(adr.get("region", "")),
            _escape_vcard(adr.get("postal_code", "")),
            _escape_vcard(adr.get("country", "")),
        ]
        lines.append(f"ADR:{';'.join(adr_fields)}")
    if url: lines.append(f"URL:{_escape_vcard(url)}")
    if note: lines.append(f"NOTE:{_escape_vcard(note)}")
    lines.append("END:VCARD")
    return "\n".join(lines)
