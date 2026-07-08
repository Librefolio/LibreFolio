Certo. Ti faccio un disegno “di prodotto” ad alto livello, non implementativo, per visualizzare dove siamo arrivati.

***

# Fondo Dashboard — struttura generale

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS                                                               │
│                                                                              │
│  [ Holdings / Composizione ] [ Performance / Contributo ]     [ Table|Chart ]│
│                                                                              │
│  Contenuto cambia in base alla tab selezionata                               │
└──────────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│ RECENT TRANSACTIONS                                                          │
│ Latest transactions, independent of selected date range                       │
│                                                                              │
│  resta per ora tabella DB-aligned / compatta                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

***

# 1. Holdings / Composizione — Tabella

## Significato

```text
Fotografia delle posizioni aperte a date_to.
Mostra cosa possiedo alla fine del periodo selezionato.
```

## Colonne

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS > HOLDINGS                                                                    [ Table | Chart ]│
├─────────────────────────────┬──────────┬────────┬──────────────┬────────┬──────────┬────────┬────────┬──────┤
│ Asset                       │ Value    │ Weight │ Unreal. P&L  │ P&L %  │ Quantity │ Price  │ PMC    │Broker│
├─────────────────────────────┼──────────┼────────┼──────────────┼────────┼──────────┼────────┼────────┼──────┤
│ 🟦 iShares Core MSCI World  │ €12,450  │ 34.2%  │ +€1,220      │ +10.9% │ 110.00   │ €113.2 │ €102.1 │Directa│
│ 🟨 BTP Italia 2030          │ €5,180   │ 14.2%  │ -€140        │ -2.6%  │ 5,000    │ 103.6  │ 106.4  │Directa│
│ 🟩 Recrowd Loan Alpha       │ €2,000   │ 5.5%   │ +€35         │ +1.8%  │ 1.00     │ €2,000 │ €1,965 │Recrowd│
│ 🟪 Semiconductor ETF        │ €3,750   │ 10.3%  │ +€410        │ +12.3% │ 22.00    │ €170.5 │ €151.8 │Directa│
└─────────────────────────────┴──────────┴────────┴──────────────┴────────┴──────────┴────────┴────────┴──────┘
```

## Note semantiche

```text
Value          = quantità posseduta a date_to × prezzo a date_to
Weight         = Value / NAV a date_to
Unreal. P&L    = Value - costo residuo della posizione
P&L %          = Unreal. P&L / costo residuo
PMC            = prezzo medio di carico / costo medio residuo unitario
Price Date     = NON colonna; eventualmente tooltip sul prezzo
```

***

# 2. Holdings / Composizione — Treemap

## Significato grafico

```text
Area   = Value della posizione a date_to
Colore = Unrealized P&L %
```

## Disegno ASCII

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS > HOLDINGS > CHART                                            │
│                                                                              │
│ Treemap esposizione                                                          │
│ Area = valore posizione        Colore = P&L non realizzato %                 │
│                                                                              │
│ ┌──────────────────────────────────────┬─────────────────────┬─────────────┐ │
│ │ 🟦 MSCI World                        │ 🟪 Semiconductor ETF │ 🟨 BTP 2030 │ │
│ │ €12,450                              │ €3,750              │ €5,180      │ │
│ │ +10.9%                               │ +12.3%              │ -2.6%       │ │
│ │ GREEN medium                         │ GREEN strong        │ RED light   │ │
│ │                                      │                     │             │ │
│ │                                      │                     │             │ │
│ ├───────────────────────┬──────────────┴─────────────┬───────┴─────────────┤ │
│ │ 🟩 Recrowd Alpha      │ 🟦 Healthcare ETF            │ Cash-like / other   │ │
│ │ €2,000                │ €1,850                       │ €900                │ │
│ │ +1.8%                 │ -0.7%                        │ 0.0%                │ │
│ │ GREEN very light      │ RED very light               │ neutral             │ │
│ └───────────────────────┴──────────────────────────────┴────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Lettura

```text
Box grande verde  = posizione importante e in guadagno latente
Box grande rosso  = posizione importante e in perdita latente
Box piccolo scuro = posizione piccola ma con rendimento percentuale estremo
```

***

# 3. Performance / Contributo — Tabella principale

## Significato

```text
Mostra quali posizioni hanno generato il P&L del periodo selezionato.
Include sia posizioni ancora aperte sia posizioni chiuse entro date_to.
```

## Colonne

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS > PERFORMANCE                                                                                   [ Table|Chart ]│
├─────────────────────────────┬────────────┬──────────────┬────────────┬────────┬────────┬──────────────┬────────────┬────────┬──────┤
│ Asset                       │ Period P&L │ Unrealized Δ │ Real. Sales│ Income │ Costs  │ Start Value  │ End Value  │ Status │Broker│
├─────────────────────────────┼────────────┼──────────────┼────────────┼────────┼────────┼──────────────┼────────────┼────────┼──────┤
│ 🟦 iShares Core MSCI World  │ +€520      │ +€480        │ €0         │ +€40   │ €0     │ €10,900      │ €12,450    │ Open   │Directa│
│ 🟪 Semiconductor ETF        │ -€180      │ -€210        │ +€45       │ €0     │ -€15   │ €3,950       │ €3,750     │ Open   │Directa│
│ 🟨 BTP Italia 2030          │ +€95       │ -€40         │ +€120      │ +€25   │ -€10   │ €5,250       │ €5,180     │ Open   │Directa│
│ 🟥 Stock XYZ                │ +€300      │ €0           │ +€300      │ €0     │ €0     │ €2,400       │ €0         │ Closed │Directa│
└─────────────────────────────┴────────────┴──────────────┴────────────┴────────┴────────┴──────────────┴────────────┴────────┴──────┘
```

## Note semantiche

```text
Period P&L =
  Unrealized Δ
+ Realized Sales
+ Income
- Costs

Start Value = valore della quantità posseduta a date_from
End Value   = valore della quantità posseduta a date_to

Status = stato a fine periodo:
  Open   = posizione ancora aperta a date_to
  Closed = posizione chiusa entro date_to
```

Quindi `Start Value` e `End Value` **non sono prezzi dell’asset**, ma valori della tua posizione.

***

# 4. Performance / Contributo — Other Period Effects

## Dove stanno

Non nella tabella principale asset.  
Li metterei come sezione separata, subito sotto la tabella Performance.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ OTHER PERIOD EFFECTS                                                         │
│ Effects that contribute to period P&L but are not linked to a specific asset │
├──────────────────────────────┬──────────────┬────────────┬──────────────────┤
│ Description                  │ Category     │ Period P&L │ Broker           │
├──────────────────────────────┼──────────────┼────────────┼──────────────────┤
│ Cash interest                │ Income       │ +€12.40    │ Directa          │
│ Broker custody fee           │ Cost         │ -€3.20     │ Directa          │
│ FX residual                  │ Other        │ +€0.18     │ —                │
│ Unallocated result           │ Other        │ -€1.05     │ —                │
└──────────────────────────────┴──────────────┴────────────┴──────────────────┘
```

## Motivo

```text
Non sono posizioni.
Non hanno quantità, PMC, valore iniziale/finale o stato posizione.
Però aiutano a riconciliare il P&L totale del periodo.
```

***

# 5. Performance / Contributo — Grafico stacked divergente

## Significato

```text
Asse Y = asset / voce
Asse X = importo P&L
Destra = componenti positive
Sinistra = componenti negative

Segmenti = componenti del P&L
Label finale = P&L netto periodo
```

## Versione concettuale

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS > PERFORMANCE > CHART                                         │
│ Stacked diverging bar chart                                                  │
│                                                                              │
│ Components:                                                                  │
│   ■ Unrealized Δ     ■ Realized Sales     ■ Income     ■ Costs               │
│                                                                              │
│                         Negative          0             Positive             │
│                           │               │                │                 │
│ MSCI World                │               │■■■■■■■■■■■ ■   │  +€520          │
│                           │               │Unreal.  Income  │                 │
│                                                                              │
│ Semiconductor ETF     ■■■■■■■             │■■               │  -€180          │
│                       Costs/Unreal.        │Realized         │                 │
│                                                                              │
│ BTP Italia 2030        ■■■                │■■■■ ■■          │  +€95           │
│                       Unreal./Costs       │Real. Income     │                 │
│                                                                              │
│ Stock XYZ                 │               │■■■■■■           │  +€300          │
│                           │               │Realized         │                 │
│                                                                              │
│ ───────────────────────────────────────────────────────────────────────────  │
│ Other period effects                                                         │
│                                                                              │
│ Cash interest            │               │■                │  +€12           │
│ Broker fee           ■   │               │                 │  -€3            │
│ FX residual              │               │▏                │  +€0.18         │
└──────────────────────────────────────────────────────────────────────────────┘
```

***

# 6. Performance chart — caso con compensazioni forti

Questo è il tuo esempio:

```text
Asset A:
  positive effects = +100
  negative effects = -99
  net P&L          = +1
```

Nel grafico lo rappresenterei così:

```text
                         Negative          0             Positive
                           │               │                │
Asset A              ■■■■■■■■■■■■■■■■■■■■■│■■■■■■■■■■■■■■■■■■■■  +€1 net
                    -€99 negative effects │ +€100 positive effects
```

Questo è importante perché così non nascondiamo il fatto che:

```text
il risultato netto è piccolo,
ma dietro c’è stato grande movimento lordo.
```

Se invece mostrassimo solo `+€1`, perderemmo informazione.

***

# 7. Performance chart — stack per segno

La regola finale la disegnerei così:

```text
Per ogni componente:
  se componente > 0 → stack a destra dello zero
  se componente < 0 → stack a sinistra dello zero
```

Esempio:

```text
Asset B:
  Unrealized Δ     -210
  Realized Sales    +45
  Income              0
  Costs             -15
  Period P&L       -180
```

Disegno:

```text
                         Negative          0             Positive
                           │               │                │
Asset B              ■■■■■■■■■■■■■■■       │■■              -€180 net
                    Unrealized + Costs     │Realized
```

Quindi:

```text
la barra non è “una sola barra impilata lineare”;
è uno stack divergente con due lati:
  lato negativo
  lato positivo
```

***

# 8. Performance chart — con Status

Lo `Status` non diventa una serie del grafico.  
Resta metadata della riga.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Performance Chart                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ MSCI World          [Open]    │■■■■■■■■■■■■■■■■■■                  +€520     │
│ Semiconductor ETF   [Open]    ■■■■■■■■■│■■                         -€180     │
│ Stock XYZ           [Closed]  │■■■■■■■■■■                           +€300     │
│ BTP Italia 2030     [Open]    ■■■│■■■■                              +€95      │
└──────────────────────────────────────────────────────────────────────────────┘
```

Nel tooltip:

```text
Asset: Stock XYZ
Status: Closed by period end
Period P&L: +€300
Unrealized Δ: €0
Realized Sales: +€300
Income: €0
Costs: €0
Start Value: €2,400
End Value: €0
Broker: Directa
```

***

# 9. Confronto finale tra Holdings e Performance

```text
┌──────────────────────────────┬───────────────────────────────────────────────┐
│ Holdings                     │ Performance                                   │
├──────────────────────────────┼───────────────────────────────────────────────┤
│ Cosa possiedo a date_to      │ Cosa ha generato P&L nel periodo              │
│ Solo posizioni aperte        │ Posizioni aperte e chiuse rilevanti           │
│ Snapshot                    │ Period-based                                  │
│ Usa Value / Weight           │ Usa Period P&L e componenti                   │
│ Ha P&L non realizzato %      │ Non ha Period %                               │
│ Treemap                     │ Stacked diverging bar chart                    │
│ Area = Value                 │ Lunghezza = componenti P&L                    │
│ Colore = Unrealized %        │ Destra positivo, sinistra negativo            │
└──────────────────────────────┴───────────────────────────────────────────────┘
```

***

# 10. Disegno compatto finale del pannello

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ YOUR POSITIONS                                                               │
│                                                                              │
│ [ Holdings ] [ Performance ]                                  [ Table|Chart ]│
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ If Holdings + Table                                                     │ │
│ │ Asset | Value | Weight | Unrealized P&L | P&L % | Qty | Price | PMC | Broker│
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ If Holdings + Chart                                                     │ │
│ │ Treemap: area = Value, color = Unrealized P&L %                         │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ If Performance + Table                                                  │ │
│ │ Asset | Period P&L | Unrealized Δ | Realized | Income | Costs |         │ │
│ │ Start Value | End Value | Status | Broker                              │ │
│ │                                                                          │ │
│ │ Other period effects                                                     │ │
│ │ Description | Category | Period P&L | Broker                            │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ If Performance + Chart                                                  │ │
│ │ Stacked diverging bar chart                                             │ │
│ │ Components stacked by sign around zero                                  │ │
│ │ Other effects shown as separated group                                  │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Questa secondo me è una rappresentazione abbastanza fedele dello stato attuale della progettazione.
