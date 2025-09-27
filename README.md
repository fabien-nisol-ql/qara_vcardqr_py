# vcardqr

Generate **vCard 4.0 (RFC 6350)** QR codes with an optional **center logo badge**.

## Quickstart

Creating a vcard

```bash
make install
❯ vcardqr --yaml examples/contact.yaml
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

## ⚖️ License & The “Tom Clause”

Copyright (c) 2025 Fabien Nisol

This project is released under the MIT License (see `LICENSE`).  
**However…** a special addendum applies to _Tom_. Yes, **you**, Tom.  
You are **strictly prohibited** from reselling this project without Fabien’s **express written approval** (a signed note or at least a cappuccino). ☕️

> Legal note: The “Tom Clause” is a humorous reminder and **not** legally binding.
> The actual terms are those in the MIT License.
