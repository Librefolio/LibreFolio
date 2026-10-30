# MF-A13 — il tasso del punto di prezzo: misura e proposta di contratto (28/10/2026)

> MF, ondata 6, base `b48694f3f`. Sola lettura: nessun codice. Origine: backlog MF-A13 (`BACKLOG_POST_1.2.md:10837`),
> [analisi T-U1](analisi-T-U1-convert_bulk-20261028.md) §6. Piano: [plan-phase01FinancialMath](plan-phase01FinancialMath.prompt.md),
> «Ondata 6». Script della misura (scratch, non nel repo): ogni riga di `price_history` del DB di prova della corsia
> (`/tmp/librefolio-r13-o6-mf`, 2 817 righe: 2 237 USD, 580 EUR), convertita in EUR e in USD; log
> `ondata6/MF-A13-misura.log`.

## 1. Cosa si misura

Oggi tre punti ricavano il tasso **dividendo** il close convertito per quello originale:

| Dove | Divisione | File di |
|---|---|---|
| `assets/observed_prices._converted` (`:125`) | `factor = close_convertito / close` → scala open, high, low | X |
| `market_series.py:169` | `fx_rate = point.close / native_close` → colonna `fx_rate` dell'esportazione per serie (`:79`, `format(…, "f")`: tutte le cifre) | J |
| `/fx/convert` | `rate = to_amount / from_amount` | X |

Il tasso «vero» del giorno è già caricato: `unit_rate_steps(...)[(src, dst)].at(day)`, lo stesso che legge il motore
(`AskedDayRates`, P3).

## 2. Risultato

| Coppia | Punti | Fattore ricavato = tasso del gradino | Differenza | Open/High/Low diversi al centesimo | … a 1e-6 | … esatti |
|---|---|---|---|---|---|---|
| EUR → USD (diretta) | 578 | **578** | — | 0 | 0 | 0 |
| USD → EUR (inversa) | 2 237 | 809 | **1 428 alla 28ª cifra** | 0 | 0 | 562 / 570 / 586 |

Esempio (USD → EUR, 24/09/2025, close 177,501395741735): fattore ricavato `0.9258866595870743156525737202`, gradino
`0.9258866595870743156525737201`.

Perché: sulla coppia inversa `convert_bulk` fa `close ÷ tasso salvato`, il gradino è `1 ÷ tasso salvato`; dividendo poi
per il close l'ultima cifra non torna. Sulla diretta è una moltiplicazione e torna sempre.

**Che cosa si vede**: nessun valore arrotondato (grafici, tabelle, AI Export arrotondato) cambia. Cambia l'ultima delle
28 cifre dove un numero è scritto per intero: la colonna `fx_rate` dell'esportazione per serie, e open/high/low a piena
precisione.

## 3. Proposta di contratto (da concordare con X tramite il coordinatore)

1. **`FAPricePoint.fx_rate: Optional[SafeDecimal]`** (schema dei prezzi, X) — il tasso unitario usato per convertire il
   punto, da `original_currency` alla valuta del punto: `steps.at(rate_day)` della riga del giorno; `None` senza
   conversione. Accanto a `original_*`, non in `backward_fill_info` (che dice *quando*, non *quanto*).
2. **`observed_prices._converted`** scala open, high, low con `fx_rate`, senza divisione.
3. **`market_series`** (J) e **`/fx/convert`** (X) leggono `fx_rate` invece di dividere.
4. **Il close** — una scelta:
   - (a) resta quello di `convert_bulk` (÷ tasso): nessun close cambia, ma sullo stesso punto `close ≠ original_close ×
     fx_rate` all'ultima cifra (1 428 punti su 2 237 della prova);
   - (b) **consigliata**: `close = original_close × fx_rate`, come il motore (MF6-1 ha già portato `current_price` a
     × 1/tasso): un punto coerente con sé stesso e col NAV. Cambia la 28ª cifra di quei 1 428 close; nessun valore
     arrotondato.
5. **AI Export**: `asset_resources.py:209` legge già `original_close` e `fx_rate_date`; con (b) un close cambia solo
   all'ultima cifra. Se il dataset scrive il close a piena precisione, il bump è di AIX (treno 13, con T-U9): da far
   dire alla sonda mirata.

Parte di MF: nessun file mio cambia (la regola «× tasso unitario» è già nella casa: `AskedDayRates`); rivedo i lotti di
X e J e scrivo i rossi di parità (diretta: 0 differenze; inversa: solo l'ultima cifra, mai un arrotondato).
