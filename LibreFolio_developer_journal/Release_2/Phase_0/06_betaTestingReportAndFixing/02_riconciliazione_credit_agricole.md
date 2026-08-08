# Riconciliazione Crédit Agricole — Excel banca ↔ LibreFolio

> Dossier numerico a supporto della sessione di verifica congiunta.
> Riferimento di verità: `Totali_05082026/Andamento Portafoglio_CAI_20260805174957.xlsx`
> (aggiornato al **05/08/2026**).

---

## 1. Il riferimento della banca

| Grandezza | Valore | Dove |
|---|---:|---|
| Ctv di carico titoli | **529.887,94 €** | somma colonna *Ctv carico (DIV)* |
| CTV titoli (valore di mercato) | **530.179,12 €** | somma colonna *CTV (EUR)* |
| P/L titoli | +291,18 € (0,05 %) | riga totali |
| **Liquidità** | **63.681,75 €** | intestazione, riga *Data Aggiornamento* |
| Titoli in dossier | 13 | — |

> ⚠️ **Punto cruciale**: nell'Excel della banca la **liquidità è un dato di intestazione**,
> separato dalla tabella titoli. I totali in fondo alla tabella (529.887,94 / 530.179,12)
> sono **solo titoli**. Confrontarli con un patrimonio netto che include la cassa è un
> confronto tra grandezze diverse — è esattamente l'equivoco all'origine del rilievo "544k vs 530k".

### Composizione del dossier

| Titolo | Quantità | Prezzo medio | Prezzo mercato | Ctv carico | CTV |
|---|---:|---:|---:|---:|---:|
| AMUNDI PIO GLOB EQ G | 1.843,575 | 10,919 | 12,406 | 20.129,41 | 22.871,39 |
| **BTP 01/03/35 3,35%** | 50.000 | 100,036 | 97,72 | **50.018,11** | **48.860,00** |
| BTP 01/08/31 0,60% | 50.000 | 87,448 | 88,05 | 43.723,98 | 44.025,00 |
| BTP 1/08/30 0,95% | 50.000 | 91,878 | 91,99 | 45.938,99 | 45.995,00 |
| BTP 1/12/2026 1,25% | 40.000 | 96,502 | 99,63 | 38.600,70 | 39.852,00 |
| BTP 1/3/32 1,65% | 50.000 | 92,356 | 91,68 | 46.177,79 | 45.840,00 |
| BTP 15/02/29 0,45% | 50.000 | 91,471 | 94,06 | 45.735,63 | 47.030,00 |
| BTP 17-11-28 FUT CUM | 85.000 | 96,070 | 95,75 | 81.659,19 | 81.387,50 |
| BTP 19-27 0,65% FOIEX | 35.000 | 97,852 | 99,74 | 34.248,34 | 35.584,14 |
| BTP 19-27 0,65 FOICUM | 40.000 | 98,357 | 99,74 | 39.342,70 | 40.667,59 |
| BTP FUT 16-11-33 CUM | 55.000 | 93,146 | 86,47 | 51.230,40 | 47.558,50 |
| BTP FUT 27-04-37 CUM | 20.000 | 90,414 | 78,74 | 18.082,70 | 15.748,00 |
| BTP PIU 25-2-33 CUM | 15.000 | 100,000 | 98,40 | 15.000,00 | 14.760,00 |
| **Totale** | | | | **529.887,94** | **530.179,12** |

---

## 2. Anomalia 1 — Costo di carico: 530k (Excel) vs 480k (dashboard) ✅ SPIEGATA

### Scala di riconciliazione

| Passo | € |
|---|---:|
| Ctv di carico banca | 529.887,94 |
| − BTP 01/03/35 3,35% *(acquisto mai importato)* | −50.018,11 |
| **= carico atteso in LibreFolio** | **479.869,83** |
| *Osservato in dashboard* | *≈ 480.000* ✅ |

**Scarto: < 0,03 %.** La quadratura è puntuale.

### Perché proprio questo titolo

Il plugin ha perso **4 righe `COMPRAVENDITA`** (dettaglio in
[`01_tassonomia_findings.md`](01_tassonomia_findings.md) §1 B1). Il tester ne aveva corrette
**3 a mano** durante la sessione (BTP PIÙ, BTP 1/3/32, Amundi). Il **BTP 01/03/35** è rimasto
l'unico non corretto — ed è esattamente il buco osservato.

> Nota di precisione: se le correzioni manuali sono state inserite all'**importo di cassa**
> anziché al controvalore secco, il carico LibreFolio risulterà più alto di circa **425,94 €**
> (rateo + commissioni del BTP 1/3/32 — vedi §4), quindi ≈ 480.295,77. Entrambi i valori
> arrotondano a "480k": la differenza va verificata sul dato reale, non pregiudica la diagnosi.

---

## 3. Anomalia 2 — Patrimonio netto: 544k (nostro) vs 530k (sito) ✅ SPIEGATA

### 3.1 L'ipotesi del doppio conteggio è smentita

> *"credo che stiamo sommando 2 volte i dividendi e interessi, uno nel P&L che li comprende e
> un altro nella liquidità"*

**Verificato e smentito.** La formula è a conteggio singolo:

```python
# backend/app/services/portfolio_engine.py:1002-1004
broker_nav = market_value + cumulative_cash
nav        = broker_nav + in_transit_mv
```

Il P&L è una grandezza **derivata**, mai risommata nel patrimonio:

```python
# backend/app/services/portfolio_engine.py:1031-1032
capital_baseline = cumulative_ecf
total_pnl        = nav - capital_baseline
```

`net_worth` e `total_gain_loss` sono assegnati da campi distinti
(`portfolio_service.py:1501` e `:1503`) e il frontend li rende separatamente:
`KpiSection.svelte:111-112` — il P&L è solo un'etichetta secondaria **sotto** il patrimonio,
mai addizionata.

L'invariante è già coperta da un test di regressione:

```python
# backend/test_scripts/test_services/test_financial/test_portfolio_service.py:411-430
"""For every returned point: nav_value == cash_value + market_value."""
assert point.nav_value == point.cash_value + point.market_value
```

Dividendi e interessi alimentano la cassa **una volta sola**, dallo stesso ramo di codice di un
deposito (`portfolio_engine.py:571-579`); e **non** toccano la `capital_baseline`, perché
`_EXTERNAL_CASH_TYPES = {DEPOSIT, WITHDRAWAL}` (`portfolio_engine.py:63`).

Che il P&L *cresca* quando arriva una cedola è **corretto**: è rendimento totale. La coincidenza
`544 − 14,6 ≈ 530` era fuorviante.

### 3.2 La spiegazione vera: stessa causa radice + confronto non omogeneo

| Passo | € |
|---|---:|
| CTV titoli banca (05/08) | 530.179,12 |
| − BTP 01/03/35 al valore di mercato (50.000 × 97,72) | −48.860,00 |
| **= titoli presenti in LibreFolio** | **481.319,12** |
| + liquidità | + *cassa* |
| **= patrimonio netto atteso** | **≈ 540 – 545 k** |

Con i due estremi plausibili della cassa:

| Ipotesi cassa | Fonte | Patrimonio netto atteso |
|---|---|---:|
| 58.822,00 | *Saldo Finale* del file movimenti (31/07/2026) | 540.141,12 |
| 63.681,75 | liquidità banca (05/08/2026) | 545.000,87 |

**Il valore osservato (≈544k) cade dentro questo intervallo.** Il "530k" del sito è il
controvalore titoli soltanto: non è mai stato confrontabile.

### 3.3 Residuo da chiarire insieme

Lo scarto tra le due ipotesi (~4,9k) è coerente con quanto riferito dal tester:

> *"I report che abbiamo si fermano a luglio, nel mentre sono arrivati circa 4k€ di pensione e
> alcune cedole di alcuni btp"*

Ulteriori sorgenti di scarto **legittime**, da non scambiare per difetti:

1. **Prezzi diversi** — LibreFolio valorizza con i propri provider, la banca con i propri.
2. **Finestra temporale** — i nostri dati arrivano al 31/07, l'Excel al 05/08.
3. **Rateo nel carico** — vedi §4.

---

## 4. Rateo e commissioni incorporati (effetto sistematico sul carico)

L'estratto conto espone **un solo importo** per operazione. Differenza rispetto al controvalore
secco della banca:

| Titolo | Cassa uscita | Ctv carico | Rateo + commissioni |
|---|---:|---:|---:|
| BTP 1/3/32 1,65% | 46.603,73 | 46.177,79 | **425,94** |
| BTP 01/03/35 3,35% | 50.683,13 | 50.018,11 | **665,02** |
| BTP PIU 25-2-33 | 15.000,00 | 15.000,00 | 0,00 |
| **Totale** | | | **1.090,96** |

**Implicazione da mettere a preventivo**: importando tutto nell'acquisto (fallback accettato dal
tester), il nostro costo di carico sarà **superiore di ~1.091 €** a quello della banca. È un
disallineamento *atteso e spiegabile*, non un errore — ma va dichiarato all'utente, altrimenti
la prossima riconciliazione fallirà per un motivo nuovo.

---

## 5. Ritenute non registrate

Tutte e **56** le righe cedola/dividendo espongono `RITENUTA` nella descrizione, per un totale di
**2.203,42 €** oggi non registrati (il reddito è importato al netto).

Verifica su un caso: `15.000 × 2,85 % ÷ 4 = 106,88` lordo − `13,36` ritenuta = **93,52** =
importo importato. ✅

Non incide sul patrimonio netto (la cassa è già netta), ma incide su **P&L lordo, reportistica
fiscale ed export AI**.

---

## 6. Protocollo per la sessione di verifica congiunta

> Da eseguire **dopo** la fix P1, sul **DB di produzione locale**, su un broker creato *ex novo*
> per non inquinare i dati corretti a mano.

### Fase A — reimport pulito

1. Nuovo broker "Crédit Agricole — verifica".
2. Import dei **3 file insieme**, come nella sessione originale.
3. Nessuna correzione manuale: l'obiettivo è misurare il plugin *da solo*.

### Fase B — controlli attesi (criteri di accettazione)

| # | Controllo | Atteso |
|---|---|---|
| 1 | Le 4 righe `COMPRAVENDITA` producono BUY | 4 BUY, **0** DEPOSIT/WITHDRAWAL generici |
| 2 | Quantità BTP dedotte dalle cedole | 50.000 / 50.000 / 15.000 |
| 3 | ISIN BTP dedotti dalle cedole | IT0005094088 / IT0005358806 / IT0005634792 |
| 4 | Fondo Amundi | **1 `field_todo` blocker** sulla quantità (non deducibile) |
| 5 | Segnalazione rateo/commissioni incorporati | avviso su BTP 1/3/32 e BTP 01/03/35 |
| 6 | Ritenute | 56 transazioni TAX, totale 2.203,42 € |
| 7 | Costo di carico totale | 529.887,94 + ~1.091 (rateo) ≈ **530.979** |
| 8 | Cassa finale | ≈ **58.822,00** (= *Saldo Finale* del file) |

### Fase C — riconciliazione finale

| Voce | Atteso |
|---|---:|
| Titoli a valore di mercato | ≈ 530.179 *(± scarto prezzi provider)* |
| + Cassa | ≈ 58.822 |
| **= Patrimonio netto** | **≈ 589.000** |

Se il controllo 8 (cassa) quadra al centesimo con il *Saldo Finale* dichiarato dalla banca,
allora **ogni movimento del file è stato interpretato**: è il test più severo e più rapido, e va
eseguito per primo.

---

## 7. Riepilogo

| Anomalia | Stato | Causa |
|---|---|---|
| Carico 530k vs 480k | ✅ Spiegata | BTP 01/03/35 mai importato (**B1**) |
| Patrimonio 544k vs 530k | ✅ Spiegata | Stesso BTP + confronto titoli-soli vs netto-con-cassa |
| Doppio conteggio dividendi/interessi | ❌ Smentita | Formula a conteggio singolo, già testata |
| Cassa in negativo durante il test | ✅ Spiegata | Acquisti degradati a `WITHDRAWAL` (**B1**) |

**Una sola fix — il ramo `COMPRAVENDITA` di P1 — chiude tre delle quattro voci.**
