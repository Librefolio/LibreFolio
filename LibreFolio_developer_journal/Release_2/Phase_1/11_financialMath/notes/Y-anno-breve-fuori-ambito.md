# L'anno breve (prima del 100) fuori dal mio ambito

Y, 25/10/2026. Base: `1a6687be7` (il mio ramo). Cerca: `grep -rn "Date.UTC(" frontend/src` e i costruttori locali
`new Date(anno, mese, giorno)`, escludendo test e client generato.

## Il difetto

`Date.UTC(24, 2, 1)` e `new Date(24, 2, 1)` leggono un anno da 0 a 99 come 1900–1999. Una data digitata all'anno 24
(`0024-03-01` al posto di `2024-03-01`, il refuso di D-P4) viene quindi un secolo sbagliata, oppure rifiutata perché il
controllo «l'anno torna uguale» non torna. Dove i dati arrivano con quattro cifre dal backend il difetto si vede solo
con un refuso, ma è proprio il caso che D-P4 vuole reggere.

**La cura** è già nel repo: `utcMs(anno, indiceMese, giorno)` in `frontend/src/lib/utils/dateOnly.ts` (una casa sola,
con test: anno 24, 1 e 99). Si sostituisce `Date.UTC(...)` con `utcMs(...)`; se il codice scrive una data a mano, l'anno va
riempito a quattro cifre (`String(anno).padStart(4, '0')`). Ogni correzione porta il suo test con `0024-03-01` e
`0001-01-01`, rosso prima. Già corretti da me: `timeSeriesAggregation.ts`, `growthLadderBuckets.ts`, `growthLadderAxis.ts`,
`growthChartTooltip.ts` e i tre helper dei lotti.

## I punti

Sono 16 righe in 12 file. «Effetto» dice che cosa succede oggi con un anno da 0 a 99.

| # | File:riga | Effetto con l'anno breve | Tipo | Proprietario probabile |
|---|---|---|---|---|
| 1 | `utils/core/parseTypedDate.ts:29` (`isRealDate`) | un anno breve digitato è **rifiutato** come «non una data vera» (l'anno del controllo di andata e ritorno torna 19xx) | rifiuta | W (campo data); tocca anche l'avviso «prima del 1900» |
| 2 | `utils/core/dateArrowStep.ts:64` (`shiftIsoDate`, giorno) | le frecce sul campo data portano `0024-03-01` a **`1924-03-02`**: salto di un secolo | sbaglia in silenzio | W (campo data) |
| 3 | `utils/core/dateArrowStep.ts:49` (`daysInMonth`) | giorni del mese letti nel 19xx; per gli anni 1–99 il bisestile coincide, sbaglia solo l'anno 0: va uniformato | quasi innocuo | W |
| 4 | `features/transactions/import/importReportSets.ts:271` (`dayNumber`) | giorni dal 1970 sfasati di un secolo: la distanza fra una data breve e una normale è sbagliata | sbaglia in silenzio | W (import) |
| 5 | `features/transactions/import/importReportSets.ts:289` (`formatIsoDay`) | l'anteprima dell'import mostra una data breve come **1924**: il refuso sparisce dalla vista | mostra altro | W (import) |
| 6 | `features/transactions/import/ImportWizardModal.svelte:3713` (`formatSetDay`) | stesso difetto di 5, copia locale | mostra altro | W (import) |
| 7 | `utils/rangeChange.ts:53` (`isCalendarDay`) | un giorno breve è **rifiutato** (stesso controllo di andata e ritorno) | rifiuta | X (dettagli asset/cambio) |
| 8 | `utils/periodChanges.ts:52` (`isoDayNumber`) | idem: giorno breve rifiutato, la variazione di periodo manca | rifiuta | X (dettagli asset/cambio) |
| 9 | `stores/core/TimeSeriesStore.ts:54` (`parseDate`) | l'intervallo di una serie con data breve è letto nel 19xx | sbaglia in silenzio | Z (prezzi) |
| 10 | `features/ai-export/aiExportOptions.ts:115` (`parseIsoDate`) | una data di snapshot breve **lancia** `TypeError` («non valida») | lancia | Z (AI Export) |
| 11 | `features/ai-export/aiExportOptions.ts:124-125` (`subtractMonths`) | il calcolo del periodo (n mesi indietro) sbaglia solo se il risultato cade prima dell'anno 100 (una fine breve lancia già al punto 10) | quasi innocuo | Z (AI Export) |
| 12 | `features/ai-export/templates/snapshotDataRenderer.ts:428` (`dateOrdinal`) | una data breve non diventa ordinale (rifiutata): la riga resta senza ordine | rifiuta | Z (AI Export) |
| 13 | `features/risk/assetSetLevels.ts:425-426` (`addMonthsClamped`) | «n mesi dopo» una data breve esce nel 19xx | sbaglia in silenzio | chi ha il rischio (da confermare: H o altro) |

Costruttori locali dello stesso difetto, a basso rischio ma da sapere:
- `components/ui/date/CalendarMonth.svelte:70,73,74`: griglia del selettore data. Oggi `min="1900"` lo nasconde. Se W toglie il
  `min` (D-P4, punto 4 dell'avviso nella UI), la griglia di un anno breve va riletta: **è un prerequisito della sua
  modifica**. W.
- `utils/core/formatAxisDate.ts:59` (`parseDisplayDate`): per un anno breve il controllo di andata e ritorno fallisce e
  la funzione dà `null`, quindi gli assi e i tooltip scrivono il testo `0024-03-01` così com'è. È un ripiego
  accettabile, anzi utile (il refuso si vede): **non lo tocco**. Se si volesse una data formattata, `Intl` con anno
  `numeric` scriverebbe «24», che si legge come 2024 ed è peggio: decisione di prodotto.

## Nota di ordine

I punti 1, 2 e 7 sono i più pesanti per D-P4: un campo data che rifiuta o salta un secolo lascia passare o nasconde il refuso
proprio dove il developer vuole l'avviso. Vanno prima, insieme all'avviso di W.
