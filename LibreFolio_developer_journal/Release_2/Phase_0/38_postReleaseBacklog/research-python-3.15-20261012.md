# Python 3.15 per LibreFolio: report di adozione (12 ottobre 2026)

## Sintesi

**Python 3.15.0** è la versione stabile più recente: rilasciata il **9 ottobre 2026** (3 giorni fa), PEP 790, in fase "bugfix". Il GIL **non** è stato sbloccato di default: il free-threading resta un build opt-in separato (`python3.15t`), ufficialmente "supportato" (PEP 779 fase II, raggiunta con la 3.14) ma non ancora il default (fase III non calendarizzata, nessuna PEP la propone). "Lazy imports" è reale e finale (PEP 810, parola chiave soft `lazy`), ma va scritto esplicitamente riga per riga, non è un comportamento automatico. Le novità più rilevanti per questo stack sono ereditate dalla 3.14: le annotazioni differite (PEP 649/749) aiutano avvio/import di Pydantic/SQLModel/FastAPI; da notare che il GC incrementale della 3.14.0 è stato **revertito** alla 3.14.5 per pressione di memoria in produzione, ed è ancora il GC generazionale classico nella 3.15. Sul piano pratico: a 3 soli giorni dal rilascio, **cvxpy, riskfolio-lib, osqp, arch, ta-lib e PyYAML non hanno ancora alcuna wheel per 3.15** (né normale né free-threaded) — un blocco concreto e verificato, non ipotetico. pydantic-core, pandas, scikit-learn, pyscipopt, scs, matplotlib richiedono solo un bump di patch/minor già disponibile su PyPI. Raccomandazione: **non adottare ora**; restare su 3.13 (supportata fino a ~ott. 2029) o valutare la 3.14 dopo la 1.2, ripetere la verifica ecosistema a inizio 2027.

---

## 1. La versione più recente di CPython e le sue novità

### 1.1 Rilascio

Python **3.15.0**, rilasciato **venerdì 9 ottobre 2026** (5.643 commit, 1.012 contributor) — **VERIFICATO**: [PEP 790](https://peps.python.org/pep-0790/), [python.org/downloads/release/python-3150](https://www.python.org/downloads/release/python-3150/), [devguide.python.org/versions](https://devguide.python.org/versions/). Oggi (12/10) è in fase "bugfix"; release successive ogni ~2 mesi per 2 anni, poi solo sicurezza fino a ~ott. 2031.

### 1.2 "Lazy imports" — PEP 810

**VERIFICATO** ([PEP 810](https://peps.python.org/pep-0810/)): Status **Final**, Python-Version 3.15, risoluzione 3-nov-2025. Non è quello che probabilmente lo sviluppatore immagina (un flag globale "automatico"): è una **nuova soft keyword `lazy`** da scrivere esplicitamente:
```python
lazy import json
lazy from pathlib import Path
```
Il modulo non viene caricato finché il nome non è usato per la prima volta. Vincoli verificati: solo a livello di modulo (non in funzioni/classi/`try`), niente `lazy from x import *` né `lazy from __future__ import`. Esiste anche un flag globale `-X lazy_imports=all` / `PYTHON_LAZY_IMPORTS=all` e un filtro programmabile `sys.set_lazy_imports_filter()` per rendere lazy solo moduli propri lasciando eager le terze parti. Per retrocompatibilità con <3.15 esiste `__lazy_modules__ = [...]` a livello di modulo. Fonte: [docs.python.org/3/whatsnew/3.15.html#pep-810](https://docs.python.org/3/whatsnew/3.15.html). Predecessore respinto: PEP 690 (import lazy *di default*) — esplicitamente fuori scope qui.

**Rilevanza: MEDIA.** Lo stack di LibreFolio importa a freddo librerie pesanti (QuantLib, cvxpy/riskfolio-lib, matplotlib, TA-Lib, scipy) che non servono a ogni richiesta. Marcare `lazy` gli import di questi moduli nei servizi che li usano solo in alcuni endpoint potrebbe ridurre il tempo di avvio di ogni worker uvicorn — ma richiede modifiche esplicite e mirate, non è un "freebie".

### 1.3 "Modi più compatti di scrivere codice"

| Novità | PEP | Versione | Rilevanza | Perché |
|---|---|---|---|---|
| Unpacking in comprehension (`[*L for L in lists]`) | 798 | 3.15 | Bassa | Zucchero sintattico, nessun impatto su stack esistente |
| `frozendict`/`sentinel` builtin | 814/661 | 3.15 | Bassa | Potrebbe sostituire pattern custom (es. sentinel per default mutabili in Pydantic), non urgente |
| `except Foo, Bar:` senza parentesi | 758 | 3.14 | Bassa | Solo leggibilità |
| `.start` files al posto di `import` in `.pth` | 829 | 3.15 | Bassa | Irrilevante per un'app containerizzata |

Nessuna di queste è "GIL unlocked" (vedi §2) né cambia in modo sostanziale il codice del backend.

### 1.4 Cosa porta la 3.14 (ereditato, visto che si parte dalla 3.13) rilevante per FastAPI/Pydantic/SQLModel

**VERIFICATO** da [docs.python.org/3/whatsnew/3.14.html](https://docs.python.org/3/whatsnew/3.14.html):

| Feature | PEP | Rilevanza | Perché |
|---|---|---|---|
| **Annotazioni differite** | 649/749 | **ALTA** | Le annotazioni non sono più valutate eager a definizione di funzione/classe/modulo, ma solo on-demand tramite funzioni "annotate" (modulo `annotationlib`, formati `VALUE`/`FORWARDREF`/`STRING`). Riduce il costo di import/avvio di moduli con molti modelli SQLModel/Pydantic e toglie l'obbligo delle stringhe per i forward-reference. **Pydantic ≥2.12.0** (7-ott-2025) ha aggiunto il primo supporto a questo meccanismo — [github.com/pydantic/pydantic/releases/tag/v2.12.0](https://github.com/pydantic/pydantic/releases/tag/v2.12.0) ("Pydantic V1 non è compatibile con Python 3.14+"). Il pin del progetto, `pydantic==2.13.5`, è **più recente** di 2.12.0 → compatibilità **VERIFICATA** per transitività di versione. Attenzione: un benchmark comunitario ([AnupCloud/python_gil_fastapi](https://github.com/AnupCloud/python_gil_fastapi)) ha dovuto patchare `pydantic 2.13.4` per un kwarg (`prefer_fwd_module`) rimosso da `typing._eval_type` su 3.14 RC2 — sintomo che la transizione ha avuto attriti reali risolti rapidamente a monte, da ri-verificare con test propri, non assumere "zero rischio" solo perché le versioni coincidono sulla carta. |
| **PEP 750 — Template string (`t"..."`)** | 750 | Bassa/Media | Nuovo tipo `string.templatelib.Template`, utile per costruire SQL/HTML/log sanificati senza concatenazione stringhe. Il progetto usa già SQLAlchemy parametrizzato e `structlog`; utilità reale ma non urgente, nessuna dipendenza lo richiede oggi. |
| **PEP 734 — `concurrent.interpreters`** | 734 | Bassa/Media | Sub-interpreter in libreria standard come alternativa più leggera ai processi per isolamento CPU-bound. Teoricamente interessante per i plugin "Tool" (oggi isolati con `multiprocessing` spawn), ma **VERIFICATO** che "molti moduli di estensione di terze parti su PyPI non sono ancora compatibili con interpreti multipli" e l'avvio/condivisione dati restano costosi (whatsnew 3.14). Da monitorare, non da adottare ora. |
| **PEP 758 — `except`/`except*` senza parentesi** | 758 | Bassa | Sintassi |
| **PEP 784 — `compression.zstd` in stdlib** | 784 | Bassa/Media | Se in futuro serve comprimere backup/report broker, evita una dipendenza esterna `zstandard`; oggi non in uso |
| **PEP 768 — debug interface esterno (`sys.remote_exec`)** | 768 | Bassa | Utile per diagnosi in produzione, non cambia il codice applicativo |
| **GC incrementale aggiunto poi RIMOSSO** | — | **ALTA (da sapere)** | Il GC a cicli è diventato incrementale in 3.14.0–3.14.4 (pause massime ridotte); ma per "segnalazioni di pressione di memoria significativa in ambienti di produzione" è stato **revertito al GC generazionale della 3.13 dalla 3.14.5 in poi**, e **la 3.15 usa lo stesso GC generazionale** (non incrementale). **VERIFICATO**: [whatsnew/3.14.html#garbage-collection](https://docs.python.org/3/whatsnew/3.14.html) + conferma esplicita in [whatsnew/3.15.html](https://docs.python.org/3/whatsnew/3.15.html) ("this is the GC now used in Python 3.14.5 and later **and Python 3.15**"). Nessuna azione di adattamento del codice LibreFolio necessaria, ma è un segnale di cautela: anche funzionalità "finite" nei whatsnew possono essere riviste in corsa. |
| **JIT sperimentale** | — | Bassa (per ora) | Ancora **esplicitamente sperimentale/opt-in** in 3.15 (richiede build da sorgente con `--enable-experimental-jit`, LLVM 21). Numeri ufficiali 3.15: +7-8% geomean x86-64 Linux, +11-12% AArch64 macOS *rispetto all'interprete tail-calling* ([python.org/downloads/release/python-3150](https://www.python.org/downloads/release/python-3150/)). Non è nei build ufficiali Docker/Homebrew usati dal progetto. |
| **Interprete "tail-calling"** | — | Bassa/Media | Nuovo tipo di interprete C (chiamate in coda tra funzioni che implementano i singoli opcode); 3-5% più veloce (3.14, solo Clang≥19 su x86-64/AArch64). **Novità 3.15**: gli installer ufficiali Windows a 64-bit lo usano ora di default. Trasparente per il codice applicativo. |
| **PEP 686 — UTF-8 default** | 686 | Bassa | Rilevante solo se il deployment non gira già in locale UTF-8 (il container Docker Debian-slim già lo fa) |

---

## 2. Free-threading (no-GIL): stato ufficiale

**Build**: non è il default. Richiede un eseguibile **separato**, `python3.15t` (o build da sorgente con `--disable-gil`). **VERIFICATO**: [whatsnew/3.13.html](https://docs.python.org/3/whatsnew/3.13.html) (introduzione), confermato invariato in 3.15 — nessuna PEP di "fase III" (default) esiste. Ricerca diretta sull'indice ufficiale delle PEP ([peps.python.org/api/peps.json](https://peps.python.org/api/peps.json)) conferma che le uniche PEP su thread/GIL sono: **703** (Final, 3.13 — meccanismo), **779** (Final, 3.14 — criteri fase II), **803** (Final, 3.15 — ABI stabile per build free-threaded). Nessuna PEP sulla fase III.

**Fasi (PEP 703/779, VERIFICATO [peps.python.org/pep-0779](https://peps.python.org/pep-0779/))**:
- **Fase I** (3.13): sperimentale.
- **Fase II** (raggiunta con **3.14**): "ufficialmente supportato ma opzionale". Criteri posti dalla PEP 779 (mar. 2025): overhead single-thread target ≤15% (allora ~10%, 3% su macOS), overhead memoria target ≤20% (allora 15-20%), API stabili, documentazione interna. La PEP conclude: *"we believe Python 3.14 is the right time frame for phase II"*.
- **Fase III** (default): **non decisa**, "lasciata a una PEP futura" — non esiste ancora, nemmeno in bozza, al 12/10/2026.

**Overhead single-thread**: whatsnew 3.14 (ottobre 2025, **VERIFICATO**): *"The performance penalty on single-threaded code in free-threaded mode is now roughly 5-10%, depending on the platform and C compiler"* — in calo rispetto al ~10%/3%(macOS) della PEP 779 di marzo 2025, grazie all'abilitazione dell'interprete adattivo specializzante (PEP 659) anche nel build free-threaded. **Non ho trovato nessun numero aggiornato ufficiale specifico per la 3.15** nel whatsnew ufficiale (ho cercato esplicitamente "overhead"/"single-thread" nel testo scaricato: compaiono solo in relazione al profiler Tachyon, non alla GIL). Cifre tipo "6-9%" circolate su blog di terze parti (nandann.com, c-sharpcorner.com) sono **NON verificate/NON primarie** — le riporto come colore, non come fatto. Overhead di memoria: +15-20% (PEP 779), con cause tecniche concrete e verificate in [docs.python.org/3/howto/free-threading-python.html](https://docs.python.org/3/howto/free-threading-python.html): stringhe internate immortali, QSBR (quiescent-state reclamation) che ritarda la liberazione di memoria per liste/dict, allocatore mimalloc al posto di pymalloc, refcounting "biased/deferred/per-thread" che tiene in vita oggetti più a lungo. Per un processo server long-running, questo significa un RSS potenzialmente "a cresta" rispetto al build standard, da monitorare.

**Immagini Docker ufficiali**: **VERIFICATO** nessuna variante free-threaded esiste **mai** esistita nel repository sorgente delle immagini ufficiali. Ho ispezionato direttamente [github.com/docker-library/python](https://github.com/docker-library/python) `versions.json`: le uniche varianti per ogni versione sono basi OS (`trixie`, `slim-trixie`, `bookworm`, `slim-bookworm`, `alpine3.24/23`, `windowsservercore-*`) — **nessun tag con suffisso `t` o `nogil` è mai stato pubblicato**. Inoltre, al 12/10/2026 (oggi), il tag Docker Hub ufficiale per la 3.15 **finale non esiste ancora**: il repo traccia ancora `3.15-rc` (→ `3.15.0rc3`), mentre 3.13 (`3.13.16`) e 3.14 (`3.14.8`) sono aggiornati. Normale: il gap storico osservato per 3.13.16 è stato di ~10 giorni dal rilascio upstream (1→11 ott. 2026) alla pubblicazione del tag Docker. Fonte: query dirette a `hub.docker.com/v2/repositories/library/python/tags` e al repo GitHub.

**Homebrew**: **VERIFICATO** — esiste una formula **dedicata e separata**, `python-freethreading` (non una variante di `python@3.13`/`@3.14`/`@3.15`), già aggiornata a **3.15.0** con binari `python3.15t`/`pip3.15t` ([formulae.brew.sh/formula/python-freethreading](https://formulae.brew.sh/formula/python-freethreading)), installabile in coesistenza col Python normale (`brew install python-freethreading`). Le formule regolari `python@3.13` (stabile: **3.13.16**, deprecazione schedulata 2029-11-01) e `python@3.15` (stabile: **3.15.0**, già disponibile) sono anch'esse verificate via API JSON ([formulae.brew.sh/api/formula/...](https://formulae.brew.sh/api/formula/python@3.13.json)).

**Cosa succede importando un'estensione C non pronta per il free-threading**: **VERIFICATO** ([docs.python.org/3/howto/free-threading-extensions.html](https://docs.python.org/3/howto/free-threading-extensions.html) + [whatsnew/3.13](https://docs.python.org/3/whatsnew/3.13.html)): un'estensione deve dichiararsi esplicitamente compatibile (slot `Py_mod_gil`/`Py_MOD_GIL_NOT_USED` per init multi-fase, o `PyUnstable_Module_SetGIL()` per init singola-fase). Se non lo fa: *"importing the extension will raise a warning and enable the GIL at runtime"* — cioè la GIL viene **riattivata per tutto il processo**, silenziosamente, per il resto dell'esecuzione (non un crash immediato). Si può forzare comunque l'opposto con la env var **`PYTHON_GIL=0|1`** o il flag **`-X gil=0|1`** ([docs.python.org/3/using/cmdline.html](https://docs.python.org/3/using/cmdline.html)) — ma forzare la GIL off nonostante un'estensione non testata rischia crash reali, perché quel codice C non è mai stato validato senza lock. Richiede **pip ≥24.1**. Esempio concreto verificato: `protobuf` non pubblica wheel `cp315t`, ma pubblica **sia** una wheel compilata (`cp310-abi3`, incompatibile con build free-threaded) **sia** una wheel universale pura-Python (`py3-none-any`); su un interprete `cp315t`, `pip`/`packaging` seleziona automaticamente quella pura-Python — degradazione silenziosa di prestazioni, non il meccanismo di "warning + riattivazione GIL" (quello scatta solo se la *stessa* estensione nativa viene caricata senza essersi dichiarata compatibile).

**Novità 3.15 — PEP 803/793/820 ("abi3t")**: **VERIFICATO**, tutte Final/3.15. Introduce una **Stable ABI dedicata al free-threading** (tag wheel `abi3t`), per permettere agli autori di estensioni di pubblicare **una sola wheel** compatibile con tutte le future versioni free-threaded di CPython ≥3.15 (come già avviene con `abi3` per i build normali), risolvendo il problema "uovo e gallina" che la PEP 779 segnalava nel 2025. Richiede però modifiche non banali al codice C (basicsize negativo, `PyObject_GetTypeData()`, nuovi hook `PyModExport_*`/`PySlot`). Supporto negli strumenti di build: meson-python, scikit-build-core, Maturin. **Nessuno dei pacchetti compilati del progetto usa ancora `abi3t`** (tutti i wheel free-threaded trovati su PyPI sono ancora per-versione, `cp314-cp314t`/`cp315-cp315t`): è un investimento futuro dell'ecosistema, non un effetto immediato.

---

## 3. Tabella di compatibilità (verificata via PyPI JSON API, 12/10/2026)

Legenda: ✅ = wheel esistente per quella build al **pin attuale**; ❌ = nessuna wheel (nemmeno in sdist pre-compilato); **abi3** = singola wheel stabile che copre anche cp315 "gratis"; **py-fallback** = pip seleziona automaticamente la wheel pura-Python se manca il binario compatibile.

### Pacchetti compilati (prioritari)

| Pacchetto (pin) | Build normale (cp315) | Build free-threaded (cp315t) | Note / azione |
|---|---|---|---|
| **pydantic-core** 2.46.5 | ❌ *al pin* | ❌ *al pin* | 2.50.1 (latest) ha entrambe → **bump necessario**. FT supportata dalla 2.29.0 (tracking). |
| **numpy** 2.5.3 | ✅ | ✅ | FT dalla 2.1.0. Nessuna azione. |
| **pandas** 3.0.5 | ❌ *al pin* | ❌ *al pin* | 3.0.6 (patch) ha entrambe → bump minimo. FT dalla 2.2.3. |
| **scipy** 1.18.1 (=latest) | ✅ | ✅ | FT dalla 1.15.0. |
| **scikit-learn** 1.9.0 | ❌ *al pin* | ❌ *al pin* | 1.9.1 (patch) ha entrambe → bump minimo. FT dalla 1.6.0. |
| **greenlet** 3.5.5 | ✅ | ✅ | FT dalla 3.5.2. ⚠️ Nota ufficiale sulla tracking page: *"fully supported on 3.15t and above, on 3.14t it may crash at runtime exit"* — rilevante perché SQLAlchemy async dipende sempre da greenlet (bridge sync↔async), a prescindere dal driver DB. |
| **SQLAlchemy** 2.0.52 | ✅ (pure-Py) | ✅ (pure-Py) | Il ramo 2.0.x pubblica **solo** `py3-none-any` (nessuna estensione C in questa release) — gira già senza acceleratori C, indipendentemente da CPython. Il ramo 2.1.x (più recente) ha invece wheel compilate `cp315`/`cp315t`. |
| **uvicorn** 0.52.4 | ✅ (pure-Py) | ✅ (pure-Py) | — |
| ↳ **httptools** (non pinnato, ma iniettato via `uvicorn[standard]` non pinnato in Dockerfile:70) | ✅ (0.9.0) | ✅ (0.9.0) | Vedi nota "gap Pipfile/Docker" sotto. |
| ↳ **uvloop** (idem) | ✅ (0.23.0) | ✅ (0.23.0) | FT dichiarata dalla 0.22.1 (tracking). |
| **websockets** 17.1 | ✅ + py-fallback | ✅ | — |
| **bcrypt** 5.0.0 (=latest) | ✅ (abi3) | ❌ *non ancora* | Solo cp313t/cp314t oggi; FT "generica" dichiarata dalla 4.3.0 ma non per 3.15t. |
| **lxml** 6.1.3 | ✅ | ✅ | Tracking page indica 7.0.0 come versione *progettata* per il supporto "ufficiale" dichiarato — ma le wheel 3.15t **esistono già** sul pin attuale 6.1.3. |
| **pillow** 12.3.0 (=latest) | ✅ | ✅ | FT dalla 11.0.0. |
| **psutil** 7.2.2 (=latest) | ✅ (abi3) | ❌ *non ancora* | Solo cp313t/cp314t oggi. |
| **pyyaml** 6.0.3 (=latest) | ❌ | ❌ | **Nessuna wheel 3.15, né normale né FT, nemmeno nell'ultima release.** sdist presente (build-from-source con libyaml, altrimenti fallback interno puro-Python più lento). |
| **ta-lib** 0.7.1 | ❌ | ❌ | 0.8.1 (latest) **ancora senza** cp315. Blocco upstream indipendente dal bump. |
| **QuantLib** 1.43 (=latest) | ✅ (abi3, floor cp39) | ❌ *non ancora* | Solo cp314t oggi. |
| **PySCIPOpt** 6.2.1 | ❌ *al pin* | ❌ *al pin* | 6.3.0 ha **entrambe** cp315/cp315t → bump consigliato. |
| **cvxpy** 1.9.2 | ❌ | ❌ | 1.9.3 (latest) **ancora senza** cp315 (si ferma a cp314/cp314t). Blocco upstream — rilevante perché riskfolio-lib dipende da cvxpy. |
| **clarabel** 0.11.1 (=latest) | ✅ (abi3, floor cp39) | ❌ (non offerta) | — |
| **osqp** 1.1.3 (=latest) | ❌ | ❌ | Blocco upstream. |
| **scs** 3.2.11 | ❌ *al pin* | ❌ *al pin* | 3.3.1 ha **entrambe** → bump consigliato. |
| **matplotlib** 3.11.1 | ❌ *al pin* | ❌ *al pin* | 3.11.2 (patch) ha **entrambe** → bump minimo. |
| **arch** 8.0.0 (=latest) | ❌ | ❌ | Blocco upstream (GARCH/volatilità). |
| **statsmodels** 0.15.0 (=latest) | ✅ | ✅ | — |
| **curl_cffi** 0.16.3 (=latest) | ✅ (abi3) | ❌ *non ancora* | Solo cp314t oggi. |
| **primp** 2.0.0 | ✅ (abi3) | ❌ | Nemmeno 2.0.1 (latest) ha cp315t (si ferma a cp314t). |
| **protobuf** 7.36.1 | ✅ (abi3 + py-fallback) | ✅ *(via py-fallback automatico)* | Nessuna wheel FT compilata, ma pip sceglie da sola `py3-none-any` — degradazione, non blocco. |
| **theine** 2.0.0 (=latest) | ✅ (pure-Py) | ✅ (pure-Py) | — |
| **riskfolio-lib** 7.0.1 | ❌ | ❌ | 7.4.0 (latest) **ancora fermo a cp314** (nessuna build 3.15, nessuna FT). Dipende inoltre da cvxpy (anch'esso bloccato). |

### Resto dei pacchetti: pure-Python, verificati `py3-none-any`/`py2.py3-none-any` al pin esatto → compatibili con qualunque CPython, 3.15 e 3.15t inclusi, senza bump

fastapi, sqlmodel, alembic, aiosqlite, pydantic, pydantic-settings, apscheduler, structlog, yfinance, pandas-ta-classic, httpx, beautifulsoup4, sqlglot, pycountry, mkdocs, mkdocs-material, starlette, python-magic, pyjwt, xlrd, openpyxl, ddgs, peewee. I due git-dep (`justetf-scraping`, `borsa-italiana-scraping`) sono puro Python per descrizione del progetto: nessun rischio wheel, da includere comunque nello smoke-test CI.

### Statistiche di contesto ecosistema (VERIFICATE)

- [pyreadiness.org/3.14](https://pyreadiness.org/3.14/): **66,9%** dei 360 pacchetti più scaricati dichiara supporto 3.14 (classifier PyPI).
- [pyreadiness.org/3.15](https://pyreadiness.org/3.15/): solo **25,0%** dichiara supporto 3.15 — **a 3 giorni dal rilascio**, coerente coi gap trovati sopra.

---

## 4. Il free-threading aumenterebbe davvero il throughput di questo server?

**L'event loop in sé no.** Con un solo loop asyncio per worker uvicorn, il lavoro I/O-bound (route async, chiamate HTTP, query SQLite via aiosqlite) resta seriale per costruzione — non c'è parallelismo da "sbloccare" lì. **VERIFICATO** su benchmark comunitario ([AnupCloud/python_gil_fastapi](https://raw.githubusercontent.com/AnupCloud/python_gil_fastapi/main/README.md), Python 3.14.0rc2, FastAPI 0.136.0, Apple M-series, `wrk -t4 -c50`): endpoint I/O-bound **372,23 → 359,53 req/s** (GIL on → off): **~1,0×**, nessun beneficio (anzi lieve rumore negativo).

**Cosa beneficia davvero — e quanto, secondo lo stesso benchmark**:
- CPU-bound offload su thread singolo (via `run_in_executor`/`to_thread`): **88,68 → 261,86 req/s = 2,95×**
- CPU-bound multi-thread (4 thread): **22,06 → 69,22 req/s = 3,14×**
- Workload misto "agent" parallelo: **239,33 → 456,64 req/s = 1,91×**

Questo mappa direttamente sui punti caldi CPU-bound-in-thread di LibreFolio: bcrypt già offloadato con `asyncio.to_thread` (bcrypt libera comunque il lock C durante il calcolo, ma più thread bcrypt in parallelo scalano su più core solo senza GIL); il motore FIFO puro-Python con `Decimal` eseguito in `to_thread`; pandas/numpy, che **già rilasciano la GIL internamente per le operazioni vettoriali C** quando girano in thread separati (quindi il beneficio marginale del free-threading lì è minore — il collo di bottiglia GIL per NumPy/pandas puro non è mai stato totale); i solver cvxpy/clarabel/osqp/scs (ma vedi §3: molti non hanno ancora wheel 3.15, figuriamoci FT); il process-pool per il parsing dei report broker e i plugin "Tool" in `multiprocessing` spawn — **questi ultimi due non traggono beneficio dal free-threading**, perché già ottengono parallelismo reale multi-processo oggi, a costo di IPC/serializzazione: il free-threading potrebbe in teoria sostituire i processi con thread più leggeri, ma solo riscrivendo quell'isolamento (rischio, non quick-win).

**Il vincolo reale è SQLite, non la GIL.** **VERIFICATO nel codice del progetto** (`backend/app/db/session.py:26-45`): `PRAGMA journal_mode=WAL` abilita lettori concorrenti e **un solo scrittore alla volta** ("WAL still admits one writer at a time"), con `busy_timeout=30000` tarato dopo un incidente reale documentato nel commento stesso (un sync storico ha tenuto il lock di scrittura per 10,3s, bloccando ogni scrittore concorrente). Il pool è esplicitamente `NullPool` (`session.py:100,139`, "each connection is independent"). **VERIFICATO anche nel sorgente di aiosqlite** ([omnilib/aiosqlite, core.py:90,177](https://github.com/omnilib/aiosqlite)): ogni `Connection` apre **un solo thread worker dedicato** che processa una coda seriale di operazioni — quindi anche con N connessioni/thread in parallelo reale (no-GIL), SQLite stesso serializza comunque le scritture a livello di file/WAL. Il free-threading non può alzare questo tetto: lo stesso identico limite esiste oggi, con o senza GIL. Dove aiuterebbe (marginalmente) è sui *lettori* concorrenti se mai diventassero CPU-bound nella deserializzazione Python dei risultati — scenario minore qui.

**Alternative già disponibili e già in uso, verificate nel repo**: il commento in `session.py:33` menziona esplicitamente che "**uvicorn now runs with several workers**" — cioè il progetto **già** scala orizzontalmente con più processi worker (ognuno con il proprio event loop e la propria GIL, isolamento totale, zero rischio di estensioni C non free-threading-safe). Il process-pool per il parsing broker e `multiprocessing` spawn per i Tool plugin sono la stessa strategia (processi, non thread) applicata al CPU-bound esplicito. Queste alternative **oggi funzionano con qualunque estensione C**, senza il rischio "GIL riattivata a runtime" discusso in §2, e senza aspettare wheel `cp315t` che per metà dello stack scientifico non esistono ancora (§3).

**In sintesi**: il free-threading potrebbe, in futuro, ridurre leggermente l'overhead di IPC/serializzazione rimpiazzando *alcuni* pool di thread Python-puro CPU-bound (motore FIFO, parsing testuale), ma: (a) non tocca l'event loop né I/O, (b) non tocca il collo di bottiglia SQLite/WAL, (c) oggi metà dei pacchetti compilati critici non ha nemmeno la wheel 3.15 normale, figuriamoci quella free-threaded, (d) le alternative (più worker uvicorn, process pool) sono già implementate e producono isolamento più sicuro rispetto a estensioni C non ancora validate senza GIL.

---

## 5. Raccomandazione

**Non adottare 3.15 ora. Non prima della 1.2 (20/10), e con cautela anche dopo.**

1. **Resta su Python 3.13 per la 1.2** (rilascio tra 8 giorni). 3.13 è appena entrata in fase "security" (PEP 719: **3.13.16**, rilasciata 1° ott. 2026, è l'**ultima bugfix release con installer binari**; da qui in poi solo patch di sicurezza *source-only* fino a ~ottobre 2029). Coerente col pin attuale del progetto (Homebrew `python@3.13` = **3.13.16**, verificato via API). Nessuna urgenza: 3 anni di sicurezza residui.

2. **Dopo la 1.2, valutare la 3.14 come tappa intermedia**, non la 3.15:
   - Ecosistema maturo (pyreadiness 66,9%), free-threading in fase II ufficiale da un anno, pydantic ≥2.12 già compatibile (pin attuale `2.13.5` lo è).
   - Build normale (con GIL) **non** free-threaded, Dockerfile `FROM python:3.14-slim`, nessun cambio di modello di concorrenza: rischio basso, beneficio = annotazioni differite + piccoli miglioramenti performance interprete.
   - Verificare comunque la tabella del §3 per 3.14 specificamente (il gap peggiore, es. cvxpy/arch/ta-lib, è quasi certamente presente anche lì finché quei progetti non pubblicano wheel per CPython N+1 — da ri-controllare puntualmente, non assumere).

3. **Rimandare la 3.15 a dopo la verifica ecosistema**, indicativamente **Q1 2027** (3-4 mesi dal rilascio, quando storicamente la curva di adozione PyPI matura): ri-controllare in particolare cvxpy, riskfolio-lib, osqp, arch, ta-lib, PyYAML su PyPI direttamente (`pypi.org/pypi/<pkg>/json`) e [pyreadiness.org/3.15](https://pyreadiness.org/3.15/).

4. **Free-threaded (`t`): non prima, non "invece"**. Nessun bump di throughput dimostrabile per il profilo di questo server (§4), nessuna immagine Docker ufficiale disponibile (dovreste costruirla voi da sorgente o usare immagini community non garantite), metà dei solver scientifici privi anche solo della wheel normale. Da rivalutare solo se in futuro: (a) l'ecosistema compilato raggiunge piena copertura `cp3XXt`/`abi3t`, (b) emergono benchmark ufficiali (non community) specifici per carichi FastAPI/SQLite comparabili al vostro, (c) il motore FIFO puro-Python o il parsing broker diventano un collo di bottiglia misurato che i processi attuali non risolvono.

**Passi concreti quando si procede (3.14 o 3.15)**:
- `Pipfile`: `python_version = "3.14"` (o 3.15); bump preventivo di pydantic-core, pandas, scikit-learn, pyscipopt, scs, matplotlib alle patch/minor che già pubblicano le wheel necessarie (§3); per cvxpy/riskfolio-lib/arch/ta-lib/osqp/PyYAML, **bloccare l'upgrade finché non pubblicano wheel**, oppure accettare build-from-source in CI (tempi più lunghi, toolchain Fortran/C richiesta) come fallback temporaneo e misurato.
- `Dockerfile`: aggiornare tutte le basi (`python:3.1X-slim` compare in più stage: frontend, pybuilder, finale) **in modo coerente**; **risolvere la discrepanza trovata**: `Dockerfile:70` installa `uvicorn[standard]` via pip **non pinnato**, separatamente da `requirements.txt`/`Pipfile.lock` (che pinnano solo `uvicorn==0.52.4` senza `uvloop`/`httptools`) — oggi questo significa che l'immagine di produzione ottiene silenziosamente `uvloop`/`httptools` non pinnati (dev/prod parity gap), e con un bump di CPython potrebbe tirare dentro una wheel incompatibile prima che voi ve ne accorgiate. Pinnare esplicitamente o eliminare l'extra.
- CI: matrice di test sulla versione target prima del merge; lint/test con `ruff --target-version` aggiornato; un passaggio con `-W error::DeprecationWarning` per intercettare API rimosse.
- Homebrew locale (macOS dev): `brew upgrade python@3.14` (o installare `python@3.15` in parallelo prima di switchare, già disponibile: **3.15.0** verificato); **non** installare `python-freethreading` come sostituto, è un formula a parte pensata per coesistere, non per sostituire l'ambiente di sviluppo standard.
- Da osservare dopo l'upgrade: RSS/memoria nel tempo (anche solo per il salto di GC in 3.14→3.14.5, per analogia con quanto già capitato in quel ciclo), tempo di cold-start worker (per capire se vale la pena investire in `lazy import` su QuantLib/cvxpy/matplotlib), e il tag Docker ufficiale `python:3.15-slim` finale (non ancora pubblicato al 12/10, atteso entro 1-2 settimane in base al precedente di 3.13.16).

---

## Fonti

**CPython / PEP / release**
- Stato versioni e EOL: https://devguide.python.org/versions/
- PEP 719 (schedule 3.13, 3.13.16 ultima bugfix con installer, EOL ~ott 2029): https://peps.python.org/pep-0719/
- PEP 790 (schedule 3.15, rilascio 9-ott-2026): https://peps.python.org/pep-0790/
- What's New in Python 3.15: https://docs.python.org/3/whatsnew/3.15.html
- What's New in Python 3.14: https://docs.python.org/3/whatsnew/3.14.html
- What's New in Python 3.13 (introduzione free-threading): https://docs.python.org/3/whatsnew/3.13.html
- Annuncio ufficiale 3.15.0: https://www.python.org/downloads/release/python-3150/
- Pagina download: https://www.python.org/downloads/

**PEP tematiche**
- PEP 810 (lazy imports, Final/3.15): https://peps.python.org/pep-0810/
- PEP 703 (GIL opzionale, Final/3.13): https://peps.python.org/pep-0703/
- PEP 779 (criteri fase II free-threading, Final/3.14): https://peps.python.org/pep-0779/
- PEP 803 (abi3t, Final/3.15): https://peps.python.org/pep-0803/ · PEP 793: https://peps.python.org/pep-0793/ · PEP 820: https://peps.python.org/pep-0820/ · PEP 788: https://peps.python.org/pep-0788/
- Indice machine-readable PEP: https://peps.python.org/api/peps.json

**Free-threading — documentazione tecnica**
- Estensioni C e free-threading (Py_mod_gil, warning+GIL riattivata): https://docs.python.org/3/howto/free-threading-extensions.html
- Guida free-threading (overhead memoria, QSBR, mimalloc): https://docs.python.org/3/howto/free-threading-python.html
- `PYTHON_GIL` / `-X gil`: https://docs.python.org/3/using/cmdline.html
- Installer macOS (free-threading "installato di default" dalla 3.15): https://docs.python.org/3/using/mac.html
- Tracking compatibilità pacchetti: https://py-free-threading.github.io/tracking/

**Readiness ecosistema**
- https://pyreadiness.org/3.14/ · https://pyreadiness.org/3.15/

**Build ufficiali**
- Docker Hub API tags: https://hub.docker.com/v2/repositories/library/python/tags · repo sorgente immagini: https://github.com/docker-library/python (file `versions.json`)
- Homebrew: https://formulae.brew.sh/formula/python-freethreading · https://formulae.brew.sh/formula/python@3.13 · (+ API JSON `/api/formula/<nome>.json`)

**Pacchetti (PyPI JSON API, consultata 12/10/2026, `pypi.org/pypi/<pacchetto>/json`)**: pydantic-core, numpy, pandas, scipy, scikit-learn, greenlet, sqlalchemy, uvicorn, httptools, uvloop, websockets, bcrypt, lxml, pillow, psutil, pyyaml, ta-lib, quantlib, pyscipopt, cvxpy, clarabel, osqp, scs, matplotlib, arch, statsmodels, curl_cffi, primp, protobuf, theine, riskfolio-lib + tutti i pacchetti puro-Python elencati nel §3.
- Pydantic 2.12.0 (primo supporto 3.14): https://github.com/pydantic/pydantic/releases/tag/v2.12.0
- cvxpy releases: https://github.com/cvxpy/cvxpy/releases
- arch releases: https://github.com/bashtage/arch/releases

**Benchmark comunitario (non ufficiale, verificato via README raw)**
- https://github.com/AnupCloud/python_gil_fastapi (raw: https://raw.githubusercontent.com/AnupCloud/python_gil_fastapi/main/README.md)

**Repository LibreFolio (verifica interna)**
- `backend/app/db/session.py:21-55,95-139` — WAL, NullPool, busy_timeout, commento sul writer singolo e sui "several uvicorn workers"
- `Dockerfile:56-70,158` — stage `pybuilder`, install `uvicorn[standard]` non pinnato, basi `python:3.13-slim`
- `Pipfile`, `Pipfile.lock`, `requirements.txt` — versioni pinnate, assenza di `uvloop`/`httptools` espliciti
- aiosqlite, modello a un thread per connessione: https://github.com/omnilib/aiosqlite (`aiosqlite/core.py:15,48,90,177`)

**Non verificato / scartato**: cifre di overhead free-threading specifiche per 3.15 da blog di terze parti (nandann.com, c-sharpcorner.com, edgarmontano.com, nihardaily.com) — non primarie, non citate come fatto; post Quansight Labs su asyncio free-threaded non raggiungibile (HTTP 429 persistente al momento della ricerca), non incluso tra le fonti verificate.
