# Third-Party Licenses & Attributions

LibreFolio is distributed under the [GNU Affero General Public License v3.0](LICENSE).
It builds on open-source components released under their own, permissive licenses.

This file exists to satisfy the **attribution clause** shared by the BSD, MIT, NCSA and
Apache-2.0 licenses. Those licenses permit redistribution in binary form on the condition
that the original copyright notice and disclaimer are reproduced *"in the documentation
and/or other materials provided with the distribution"*. Because LibreFolio is published
as a Docker image that bundles these packages, that clause applies to us, and this document
is the material that fulfils it.

> **Compatibility.** Every component listed below is under a permissive, GPL-compatible
> license (BSD-2, BSD-3, MIT, NCSA, Apache-2.0, PSF). None of them imposes a condition that
> conflicts with LibreFolio being licensed under AGPL-3.0. Apache-2.0 is compatible with
> GPL-3.0/AGPL-3.0 (it is *not* compatible with GPL-2.0-only, which does not apply here).

Versions below are the ones pinned in [`requirements.txt`](requirements.txt). The complete,
unabridged license text of every package is shipped inside the Docker image under
`site-packages/<package>-<version>.dist-info/`, and is also available at each project's
repository linked in the tables.

---

## 🎨 Brand icon assets

The X, Reddit, Facebook, Instagram and TikTok SVG paths in `SocialIcon.svelte` come from
[Simple Icons](https://github.com/simple-icons/simple-icons), dedicated to the
public domain under [CC0 1.0 Universal](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md).
Sources: [X](https://github.com/simple-icons/simple-icons/blob/develop/icons/x.svg)
[Reddit](https://github.com/simple-icons/simple-icons/blob/develop/icons/reddit.svg),
[Facebook](https://github.com/simple-icons/simple-icons/blob/develop/icons/facebook.svg),
[Instagram](https://github.com/simple-icons/simple-icons/blob/develop/icons/instagram.svg)
and [TikTok](https://github.com/simple-icons/simple-icons/blob/develop/icons/tiktok.svg).
Brand names and trademarks remain the property of their respective owners.

The account badges of the Scalable Capital import plugins — `chart-line-fill` and
`piggy-bank-fill`, drawn into `backend/app/services/brim_providers/static/scalable/*.png` and
`frontend/static/icons/brokers/scalable-*.png` from the sources in `scripts/assets/brokers/glyphs/` —
come from [Phosphor Icons](https://github.com/phosphor-icons/core), the same icons the LibreFolio
exporter shows, distributed under the MIT License:

```text
MIT License

Copyright (c) 2023 Phosphor Icons

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 📉 Risk Analysis stack

These are the libraries powering the Risk Analysis subsystem (simulation, optimisation,
estimation and technical indicators).

### Riskfolio-Lib 7.0.1 — BSD 3-Clause

Portfolio optimisation and risk-contribution analytics.
<https://github.com/dcajasn/Riskfolio-Lib>

```text
Copyright (c) 2020-2025, Dany Cajas
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
[...] Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution. [...]
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES [...] ARE DISCLAIMED.
```

### QuantLib 1.43 — BSD 3-Clause ("QuantLib license")

Quantitative finance library used for the simulation engine. The PyPI `QuantLib`
package contains the SWIG-generated Python bindings for the QuantLib C++ library.
<https://www.quantlib.org/> · <https://github.com/lballabio/QuantLib> ·
<https://github.com/lballabio/QuantLib-SWIG>

QuantLib is released under a BSD 3-Clause style license with an extensive
multi-contributor copyright list, beginning with:

```text
Copyright (C) 2000, 2001, 2002, 2003 RiskMap srl
Copyright (C) 2001, 2002, 2003 Nicolas Di Césaré
[... and many further contributors ...]

QuantLib is free software: you can redistribute it and/or modify it under the
terms of the QuantLib license. [...] This program is distributed in the hope
that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```

The authoritative and complete notice is
[`LICENSE.TXT` in the QuantLib repository](https://github.com/lballabio/QuantLib/blob/master/LICENSE.TXT)
and [`LICENSE.TXT` in QuantLib-SWIG](https://github.com/lballabio/QuantLib-SWIG/blob/master/LICENSE.TXT).

### pandas-ta-classic 0.6.52 — MIT

Technical-analysis indicator library, a maintained fork of `pandas-ta`.
<https://github.com/xgboosted/pandas-ta-classic>

```text
Copyright (c) 2021+ pandas-ta contributors
Copyright (c) 2024+ pandas-ta-classic contributors (xgboosted/pandas-ta-classic)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction [...]

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND [...]
```

### TA-Lib — BSD 2-Clause (Python wrapper) / BSD 3-Clause (C library)

Native technical-analysis routines. LibreFolio depends on the Python wrapper
`TA-Lib 0.7.1`, which in turn links the TA-Lib C library.

- Python wrapper: <https://github.com/TA-Lib/ta-lib-python> — maintained by John Benediktsson
  (`mrjbq7`). Released under the BSD 2-Clause License; the upstream `LICENSE` file states the
  BSD 2-Clause terms but omits an explicit copyright-holder line.
- C library: <https://github.com/TA-Lib/ta-lib> — BSD 3-Clause.

```text
Copyright (c) 1999-2026, Mario Fortier          # TA-Lib C library

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
[...] Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution. [...]
```

### Supporting numerical & statistical libraries

| Package | Version | License | Copyright notice |
|---------|---------|---------|------------------|
| [cvxpy](https://github.com/cvxpy/cvxpy) | 1.9.2 | Apache-2.0 | `Copyright 2017 Steven Diamond` (and the CVXPY authors) |
| [arch](https://github.com/bashtage/arch) | 8.0.0 | NCSA (University of Illinois/NCSA Open Source License) | `Copyright (c) 2017 Kevin Sheppard. All rights reserved.` |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | 1.9.0 | BSD-3-Clause | `Copyright (c) 2007-2026 The scikit-learn developers.` |
| [statsmodels](https://github.com/statsmodels/statsmodels) | 0.14.6 | BSD-3-Clause | `Copyright (C) 2006, Jonathan E. Taylor`<br>`Copyright (c) 2006-2008 Scipy Developers.`<br>`Copyright (c) 2009-2018 statsmodels Developers.` |
| [astropy](https://github.com/astropy/astropy) | 8.0.1 | BSD-3-Clause | `Copyright (c) 2011-2026, Astropy Developers` |

`cvxpy`, `arch`, `scikit-learn`, `statsmodels` and `astropy` are pulled in as dependencies of
Riskfolio-Lib. `cvxpy` ships no `NOTICE` file, so Apache-2.0 §4(d) imposes no additional
obligation beyond reproducing the license itself.

---

## 🧮 Core scientific stack

| Package | Version | License | Copyright notice |
|---------|---------|---------|------------------|
| [NumPy](https://github.com/numpy/numpy) | 2.5.1 | BSD-3-Clause (with bundled 0BSD / MIT / Zlib / CC0-1.0 components) | `Copyright (c) 2005-2025, NumPy Developers.` |
| [SciPy](https://github.com/scipy/scipy) | 1.18.0 | BSD-3-Clause | `Copyright (c) 2001-2002 Enthought, Inc. 2003, SciPy Developers.` |
| [pandas](https://github.com/pandas-dev/pandas) | 3.0.5 | BSD-3-Clause | `Copyright (c) 2008-2011, AQR Capital Management, LLC, Lambda Foundry, Inc. and PyData Development Team`<br>`Copyright (c) 2011-2026, Open source contributors.` |
| [Matplotlib](https://github.com/matplotlib/matplotlib) | 3.11.1 | Matplotlib License (PSF-based, BSD-compatible) | © 2012-  Matplotlib Development Team; © 2002-2011 John D. Hunter |

---

## 🌐 Application stack

The remaining runtime dependencies are permissively licensed (MIT, BSD or Apache-2.0).
The most prominent ones:

| Package | License | Project |
|---------|---------|---------|
| FastAPI | MIT | <https://github.com/fastapi/fastapi> |
| Starlette | BSD-3-Clause | <https://github.com/encode/starlette> |
| Uvicorn | BSD-3-Clause | <https://github.com/encode/uvicorn> |
| Pydantic | MIT | <https://github.com/pydantic/pydantic> |
| SQLAlchemy | MIT | <https://github.com/sqlalchemy/sqlalchemy> |
| SQLModel | MIT | <https://github.com/fastapi/sqlmodel> |
| Alembic | MIT | <https://github.com/sqlalchemy/alembic> |
| httpx | BSD-3-Clause | <https://github.com/encode/httpx> |
| APScheduler | MIT | <https://github.com/agronholm/apscheduler> |
| structlog | Apache-2.0 / MIT | <https://github.com/hynek/structlog> |
| yfinance | Apache-2.0 | <https://github.com/ranaroussi/yfinance> |
| Beautiful Soup | MIT | <https://www.crummy.com/software/BeautifulSoup/> |
| MkDocs · MkDocs Material | BSD-2-Clause · MIT | <https://github.com/mkdocs/mkdocs> · <https://github.com/squidfunk/mkdocs-material> |
| SvelteKit · Svelte | MIT | <https://github.com/sveltejs/kit> |
| Tailwind CSS | MIT | <https://github.com/tailwindlabs/tailwindcss> |
| Apache ECharts | Apache-2.0 | <https://github.com/apache/echarts> |
| Lucide | ISC | <https://github.com/lucide-icons/lucide> |
| Zodios · Zod | MIT | <https://github.com/ecyrbe/zodios> · <https://github.com/colinhacks/zod> |
| Playwright | Apache-2.0 | <https://github.com/microsoft/playwright> |

A machine-readable, always-current inventory can be produced from a running install with:

```bash
pip install pip-licenses && pip-licenses --format=markdown --with-urls
npm --prefix frontend ls --all --json
```

---

## 📄 PDF preview

The file preview shows PDFs with [EmbedPDF](https://github.com/embedpdf/embed-pdf-viewer), which runs the
[PDFium](https://pdfium.googlesource.com/pdfium/) engine compiled to WebAssembly. The image ships that engine and the
fallback fonts below, so previewing a PDF contacts no third party. Only a PDF that needs Chinese, Japanese or Korean
fallback fonts still fetches them from jsDelivr (Noto CJK, SIL OFL 1.1): tens of megabytes each, too large to ship.

| Component | Version | Shipped as | License | Copyright notice |
|-----------|---------|------------|---------|------------------|
| [EmbedPDF](https://github.com/embedpdf/embed-pdf-viewer) (`@embedpdf/*`) | 2.14.3 | JavaScript bundle | MIT | `Copyright (c) 2024-2025 CloudPDF, Ji Chang` |
| [PDFium](https://pdfium.googlesource.com/pdfium/) (in `@embedpdf/pdfium`) | 2.14.3 | `pdfium.wasm` | BSD-3-Clause | `Copyright 2014 PDFium Authors. All rights reserved.` |
| [Noto Sans](https://github.com/notofonts/latin-greek-cyrillic) — Regular, Italic, Bold, Bold Italic | `@embedpdf/fonts-latin` 1.0.0 | `.ttf` | SIL Open Font License 1.1 | `Copyright 2022 The Noto Project Authors` |
| [Noto Naskh Arabic](https://github.com/notofonts/arabic) — Regular, Bold | `@embedpdf/fonts-arabic` 1.0.0 | `.ttf` | Apache-2.0 | `Copyright 2014 Google Inc. All Rights Reserved.` |
| [Noto Sans Hebrew](https://github.com/notofonts/hebrew) — Regular, Bold | `@embedpdf/fonts-hebrew` 1.0.0 | `.ttf` | Apache-2.0 | `Copyright 2012 Google Inc. All Rights Reserved.` |

The fonts ship unmodified, under their Reserved Font Names, and every file carries its license in its own metadata
(`name` table, IDs 13 and 14). The Arabic and Hebrew files are older Noto releases: their metadata states Apache-2.0,
while the `@embedpdf/fonts-*` packages that carry them declare OFL-1.1; the notices above follow the font files. Both
licenses are permissive and compatible with AGPL-3.0.

```text
PDFium — Copyright 2014 PDFium Authors. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
[...] Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution. [...]
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES [...] ARE DISCLAIMED.
```

<details>
<summary>SIL Open Font License 1.1 — full text, as required for the Noto Sans files</summary>

```text
Copyright 2022 The Noto Project Authors (https://github.com/notofonts/latin-greek-cyrillic)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
https://openfontlicense.org

SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

</details>

---

## 📚 Citation requests

These are **courtesy requests from the authors**, not license obligations. We honour them here.

**Riskfolio-Lib** — the author asks that academic and professional work using the library cite it:

```bibtex
@misc{riskfolio,
      author = {Dany Cajas},
      title  = {Riskfolio-Lib (7.0.1)},
      year   = {2026},
      url    = {https://github.com/dcajasn/Riskfolio-Lib},
}
```

**Astropy** — the Astropy project requests acknowledgement in published work; see
<https://www.astropy.org/acknowledging.html>.

---

## 🙏 Acknowledgements

LibreFolio would not exist without the work of the QuantLib contributors, Dany Cajas
(Riskfolio-Lib), Mario Fortier (TA-Lib), Kevin Sheppard (arch), and the maintainers of the
pandas, NumPy, SciPy, FastAPI and Svelte ecosystems. Thank you.

---

*If you believe an attribution here is incomplete or incorrect, please
[open an issue](https://github.com/Librefolio/LibreFolio/issues) — we will fix it promptly.*
