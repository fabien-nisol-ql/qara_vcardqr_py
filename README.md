# vcardqr

Generate **vCard 4.0 (RFC 6350)** QR codes with an optional **center logo badge**.

## Quickstart

Creating a vcard

```bash
make install
❯ vcardqr --yaml examples/team.yaml
✅ QR code generated: /Users/fnisol/git/qara_vcardqr_py/out/John.Doe-512px.png
```

Parsing a qrcode (First execution can take up to 25 sec, python's fault)

```bash
❯ vcardqr --parse out/John.Doe-512px.png
⏳ Loading OpenCV (first time can take a while)...
BEGIN:VCARD
VERSION:4.0
N:Doe;John;;;
FN:John Doe
ORG:QARALink SA
TITLE:QRcode Manager
EMAIL:jdoel@qaralink.com
TEL;TYPE=cell:+41 79 123 45 67
TEL;TYPE=work:+41 44 987 65 43
ADR:;;Bahnhofstrasse 1;Zürich;ZH;8001;Switzerland
URL:https://qaralink.dev
NOTE:Let’s talk AI & MedTech
END:VCARD
✅ Parsed 1 QR payload(s) from out/John.Doe-512px.png
```

## 📄 YAML Configuration Format

The CLI accepts a single YAML file via `--yaml`.  
That YAML can contain **defaults** (applied to all persons) and a list of **persons**,  
each of which generates a QR code.

### Top-level structure

```yaml
defaults: <map>   # optional; default values for vcard/qr
persons: # list of person YAML configs
  - vcard: { ... }
    qr: { ... }
  - vcard: { ... }
    qr: { ... }
```

---

### 🔹 `vcard` section

Defines fields according to [RFC6350 vCard 4.0](https://www.rfc-editor.org/rfc/rfc6350).  
Minimal required fields: `given_name` and `family_name`.

Example:

```yaml
vcard:
  given_name: John
  family_name: Doe
  fn: John Doe
  org: QARALink SA
  title: QRcode Manager
  emails:
    - jdoe@example.com
  tels:
    cell: "+41 79 123 45 67"
    work: "+41 44 987 65 43"
  adr:
    street: Bahnhofstrasse 1
    locality: Zürich
    region: ZH
    postal_code: "8001"
    country: Switzerland
  url: https://qaralink.dev
  note: "Let’s talk AI & MedTech"
```

---

## YAML format

### 🔹 `qr`

Defines QR code generation options.

| Key              | Type   | Default | Description                                        |
|------------------|--------|---------|----------------------------------------------------|
| `out`            | string | —       | Explicit output file (overrides everything).       |
| `out_pattern`    | string | —       | Output file pattern (see placeholders).            |
| `logo`           | string | —       | Path to a logo image (relative to this YAML file). |
| `box_size`       | int    | 12      | Size of each QR module (pixels).                   |
| `border`         | int    | 4       | Quiet zone border size (modules).                  |
| `logo_scale`     | float  | 0.22    | Logo size relative to QR code.                     |
| `badge_rounding` | int    | 16      | Rounding of the logo badge (px).                   |
| `badge_padding`  | int    | 12      | Padding around the logo badge (px).                |
| `size_cm`        | float  | 3.0     | Final QR size in centimeters.                      |
| `size_px`        | int    | —       | Final QR size in pixels (overrides `size_cm`).     |
| `dpi`            | int    | 300     | Output DPI for cm→px conversion.                   |

---

### 🔹 Output patterns

`qr.out_pattern` supports placeholders in `{}` that resolve to vCard fields or YAML paths.  
Examples:

- `"out/{vcard.given_name}.{vcard.family_name}.png"`
- `"cards/{vcard.family_name}-{qr.size_px}px.png"`
- `"out/{firstName}_{lastName}.png"`

Sanitization: characters outside `[A-Za-z0-9._-]` are replaced with `_`.

---

### 🔹 Example: defaults + persons

```yaml
defaults:
  qr:
    logo: ./logo.png
    out_pattern: "out/{vcard.given_name}.{vcard.family_name}.png"
    size_cm: 3.5

persons:
  - vcard:
      given_name: Alice
      family_name: Smith
      emails: [ alice@example.com ]
      tels: { cell: "+41 79 123 45 67" }
  - vcard:
      given_name: Bob
      family_name: Brown
      emails: [ bob@example.com ]
      tels: { work: "+41 44 987 65 43" }
      note: "Ask me about AI in MedTech!"
```

Running:

```bash
vcardqr --yaml team.yaml
```

Will generate:

- `out/Alice.Smith.png`
- `out/Bob.Brown.png`

(both with the default logo, size, etc.)

---

## ⚖️ License & The “Tom Clause”

Copyright (c) 2025 Fabien Nisol

This project is released under the MIT License (see `LICENSE`).  
**However…** a special addendum applies to _Tom_. Yes, **you**, Tom.  
You are **strictly prohibited** from reselling this project without Fabien’s **express written approval** (a signed note
or at least a cappuccino). ☕️

> Legal note: The “Tom Clause” is a humorous reminder and **not** legally binding.
> The actual terms are those in the MIT License.
