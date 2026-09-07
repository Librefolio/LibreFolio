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
