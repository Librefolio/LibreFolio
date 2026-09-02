# 04 — Provider (asset / FX / BRIM)

> `asset_source_providers/` (7 file), `fx_providers/` (7), `brim_providers/` (32),
> `brim_provider.py`, `provider_registry.py`
> Gravità massima: 🟡

---

## Sintesi

Il sistema a plugin funziona: 29 provider BRIM, 6 provider asset e 4 provider FX vivono
sotto un registry con auto-discovery, e il pattern regge senza modifiche al core quando
si aggiunge un broker. Questa è la parte del progetto che ha scalato meglio.

Il prezzo di quella scalabilità è la **ripetizione**: 35 metodi `parse` superano la
soglia di complessità, quasi tutti con la stessa forma. Non è codice sbagliato, è codice
copiato — ogni nuovo broker parte da quello precedente e ne eredita la struttura.

Un solo reperto riguarda il codice morto, ed è un caso di **deriva documentale** più che
di codice inutile.

---

## Metriche

| Area | File | Righe | Rilievi ruff |
|---|---:|---:|---:|
| `brim_providers/` | 32 | 11 700 | ~60 |
| `asset_source_providers/` | 7 | 3 745 | ~51 |
| `fx_providers/` | 7 | 1 568 | ~20 |
| `brim_provider.py` (base) | 1 | — | 12 |
| `provider_registry.py` | 1 | — | 7 |

**35 metodi sopra soglia di complessità in `brim_providers/`** — più di uno per file.

I file con più rilievi: `yahoo_finance.py` (22), `brim_provider.py` (12),
`scheduled_investment.py` (12), `justetf.py` (10).

---

## Reperti

### 🟡 D1 — 35 metodi `parse` sopra soglia, tutti con la stessa forma

I metodi `parse` dei provider BRIM si concentrano tutti nella stessa fascia:

| Complessità | Provider |
|---:|---|
| 26 | `broker_swissquote.py:177` |
| 24 | `broker_trading212.py:186` |
| 23 | `broker_xtb.py:194`, `broker_saxo.py:187`, `broker_rabobank.py:149`, `broker_investimental.py:186` |
| 22 | `broker_schwab.py:221`, `broker_parqet.py:138` |
| 21 | `broker_traderepublic.py:133` |
| 15 | `broker_revolut.py:339` (`_parse_invest`) |
| 12 | `broker_revolut.py:458` (`_parse_crypto`) |
| 11 | `broker_relai.py:118` |

Che dodici funzioni diverse, scritte da autori diversi in momenti diversi, atterrino
tutte fra 21 e 26 non è casuale. Significa che **stanno risolvendo lo stesso problema**:
leggere righe CSV, normalizzare date e importi, mappare i tipi operazione, gestire i
casi limite del broker.

La parte specifica del broker — mappatura colonne, formati numerici, nomi dei tipi
operazione — è una frazione del totale. Il resto è ripetuto 29 volte.

**Rimedio**: estrarre nella classe base `brim_provider.py` gli helper condivisi
(normalizzazione date, parsing importi con separatori localizzati, mappatura tipi
operazione via dizionario dichiarativo), lasciando ai provider solo la configurazione
specifica.

**Attenzione**: è l'intervento a rischio più alto dell'intero audit. Ogni provider ha i
suoi casi limite scoperti sul campo con file reali, e una generalizzazione affrettata li
perderebbe silenziosamente. Se si procede, va fatto **un provider alla volta**,
verificando i file di esempio ad ogni passo — non con un refactoring di massa.

L'alternativa conservativa: lasciare stare. 29 `parse` da 23 punti sono gestibili, se
ognuno è isolato e testato.

---

### 🟡 D2 — `provider_registry.get_provider` e `list_plugin_classes` inutilizzate

**Dove**: `provider_registry.py:232` e `:88`

```python
@classmethod
def get_provider(cls, code: str):
    return cls.get_plugin(code)

@classmethod
def get_provider_instance(cls, code: str, **kwargs):
    return cls.get_plugin_instance(code, **kwargs)
```

Sono alias di una riga. `get_provider_instance` è usata ovunque; `get_provider` da
nessuno.

> **Tracciatura della logica**: è un alias puro — `cls.get_plugin(code)` è la vera
> implementazione ed è viva. **Nessuna logica va persa.**

Il problema non è il codice morto, è la **deriva documentale**: il docstring di
`fx_providers/__init__.py` dice al lettore di usare `get_provider`, mentre l'intero
codebase usa `get_provider_instance`. Chi segue la documentazione ottiene una classe
dove si aspettava un'istanza.

**Rimedio**: correggere il docstring in `fx_providers/__init__.py`. Poi, sull'alias:
rimuoverlo, oppure tenerlo con un commento che chiarisca la differenza
`classe vs istanza`. La prima è più pulita, ma va verificato che nessuna guida esterna
o plugin di terze parti lo usi.

`list_plugin_classes` (riga 88) è nella stessa categoria — API del registry mai
esercitata. Utile per introspezione, inutile finché nessuno introspeziona.

---

### 🟡 D3 — `yahoo_finance.py`: 22 rilievi, il provider più problematico

**Dove**: `backend/app/services/asset_source_providers/yahoo_finance.py`

| Regola | N | Significato |
|---|---:|---|
| `TRY301` | 5 | `raise` dentro `try` — usare `else` o estrarre |
| `ARG002` | 5 | argomenti di metodo mai usati |
| `TRY300` | 4 | `return` prima di `except` |
| `SIM108` | 3 | `if/else` esprimibile come ternario |
| `S110` | **2** | `try/except/pass` silenzioso |
| `C901` | 2 | complessità, fra cui `get_history_value` (31) |

I due `S110` (righe 357 e 630) sono i più rilevanti: Yahoo Finance è la fonte prezzi più
usata e la più instabile. Un fallimento inghiottito senza log significa che quando i
prezzi smettono di aggiornarsi, non c'è traccia del perché.

`get_history_value` a complessità 31 è la funzione più complessa di tutti i provider
asset — gestisce fallback su intervalli, valute e simboli alternativi.

**Rimedio prioritario**: aggiungere `logger.debug(..., exc_info=True)` ai due
`except: pass`. Costo: due righe. Beneficio: diagnosticabilità del provider più critico.

---

### 🟢 D4 — 6 `pass` superflui in `brim_provider.py`

`PIE790` — statement `pass` in corpi che contengono già un docstring, tipicamente
metodi astratti:

```python
@abstractmethod
def parse(self, ...) -> ...:
    """..."""
    pass   # ← superfluo
```

Rimozione automatica sicura (`ruff --fix`). Rientra negli autofix della Fase F.

---

### 🟢 D5 — `scheduled_investment.py` e `justetf.py`

12 e 10 rilievi rispettivamente, distribuiti sulle stesse famiglie (`TRY`, `SIM`,
`ARG`). Nessun singolo problema grave; è debito diffuso di stile che si risolve
progressivamente abilitando le regole in modo permanente.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Log nei due `S110` di `yahoo_finance.py` (357, 630) | nullo | nullo |
| 2 | Correggere il docstring di `fx_providers/__init__.py` (`get_provider` → `get_provider_instance`) | nullo | nullo |
| 3 | Rimuovere i 6 `pass` superflui (autofix) | nullo | nullo |
| 4 | Decidere su `get_provider` / `list_plugin_classes`: rimuovere o documentare | basso | basso |
| 5 | Ridurre `get_history_value` (31) in `yahoo_finance.py` | medio | medio |
| 6 | Estrarre helper condivisi dai `parse` BRIM — **un provider alla volta** | alto | **alto** |

I primi tre costano complessivamente pochi minuti e non possono rompere nulla.

L'intervento 6 è il più discutibile dell'audit. La duplicazione è reale e misurabile, ma
i provider BRIM sono la superficie che tocca i dati reali degli utenti: un errore di
parsing non si manifesta come eccezione, si manifesta come **transazione importata
sbagliata**. Il beneficio della deduplicazione va pesato contro questo rischio, e la mia
raccomandazione è di non affrontarlo in un ciclo di pulizia generale.
