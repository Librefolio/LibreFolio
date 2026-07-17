FIFO UI v2 — Piano di rimedio e consolidamento visuale

Stato: piano ad alto livello
 Ambito: rifinitura del Gantt, arricchimento del grafico WAC, completamento tabella e modale, semplificazione del grafico comparativo
 Vincolo: preservare il FifoLotEngine, l’endpoint bulk e le interazioni già funzionanti, intervenendo sul backend solo quando mancano dati indispensabili.

1. Obiettivo

L’implementazione attuale ha raggiunto una base funzionale valida:

✓ ricostruzione FIFO;
✓ LONG e SHORT;
✓ Gantt temporale;
✓ selezione multipla;
✓ marker transazionali;
✓ grafici comparativi temporali;
✓ modale di custodia;
✓ sincronizzazione WAC/Gantt.


La nuova fase deve migliorare la chiarezza informativa eliminando:

- disallineamento tra gli assi temporali;
- ridondanze tra tabella e legenda;
- informazioni economiche mancanti nella tabella;
- ambiguità nella modalità Valore;
- accessibilità insufficiente al dettaglio del lotto;
- comportamento errato delle serie durante l’hover;
- semantica incompleta della modalità percentuale del primo grafico.


Il risultato finale deve permettere di rispondere chiaramente a quattro domande:

WAC / Performance:
come si sono mossi mercato, costo medio e performance della posizione?

Gantt:
quando è nato il lotto, quanto è rimasto aperto e presso quale broker?

Tabella:
qual è lo stato economico e quantitativo corrente di ogni lotto?

Confronto:
quanto valore e rendimento hanno prodotto i lotti selezionati?

2. Principi invarianti

La rifinitura deve preservare:

- selezione multipla governata esclusivamente dalla tabella;
- doppio click e pulse reciproco Gantt ↔ tabella;
- asse temporale condiviso tra primo grafico e Gantt;
- quantità assolute nei lotti;
- spessore del Gantt proporzionale alla quantità;
- colore del Gantt associato al broker;
- caricamento dati tramite endpoint bulk;
- calcoli finanziari esclusivamente nel backend;
- supporto i18n completo;
- componenti LibreFolio già esistenti.


Non devono essere riprogettati:

FifoLotEngine
formule FIFO
matematica LONG/SHORT
algoritmo di transfer
algoritmo di split
contratto generale dell’endpoint bulk


salvo evidenze di dati mancanti necessarie alle nuove visualizzazioni.

3. Gantt — eliminazione della colonna fissa
3.1 Problema attuale

Il Gantt utilizza una colonna HTML fissa per l’identità del lotto e una seconda area per la timeline:

┌──────────────────────────┬───────────────────────────────────────────┐
│ Lotto 17/02              │      Directa · 2 ━━━━━━━━━━━━━━━━━━━━→  │
│ Lotto 04/03              │       Directa · 2 ━━━━━━━━━━━━━━━━━━━→  │
└──────────────────────────┴───────────────────────────────────────────┘


La struttura produce:

disallineamento rispetto all’asse X del grafico WAC;
duplicazione di lot, broker e data;
spazio orizzontale sottratto alla timeline;
label immobili durante zoom e traslazione.
3.2 Struttura desiderata

La colonna fissa deve essere rimossa.

Ogni lotto deve essere rappresentato interamente nella coordinata temporale:

WAC
│  1 ott        1 gen        1 apr        1 lug
├──────────────────────────────────────────────────────────────┤

Gantt
│  1 ott        1 gen        1 apr        1 lug
├──────────────────────────────────────────────────────────────┤
│ ●━━ Lotto 17/02/2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━→
│    ●━━ Lotto 04/03/2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━→
│         ●━━ Lotto 01/04/2025 · Directa · 1 ━━━━━━━━━━━━━━━━→
│              ●━━ Lotto 02/05/2025 · Directa · 1 ━━━━━━━━━━━→


Il grafico WAC e il Gantt devono condividere:

grid.left
grid.right
xAxis min/max
dataZoom
pan
crosshair

3.3 Label del segmento

La label deve essere contenuta nel segmento:

Lotto 17/02/2025 · Directa · 2


La label:

scorre insieme alla timeline;
viene clippata quando il segmento è troppo corto;
viene riposizionata sul primo tratto visibile se il lotto nasce prima del range;
non resta fissata al bordo sinistro.

Esempio di segmento precedente al range:

←━━ Lotto 17/02/2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━→


Esempio di segmento corto:

●━━ Lotto 17/02/2025…


Il tooltip conserva sempre il testo completo.

3.4 Informazioni visuali

Non ripetere l’icona dell’asset, perché tutti i lotti appartengono allo stesso asset già identificato nell’header.

Nel segmento possono comparire:

nome lotto;
data completa giorno/mese/anno;
icona broker;
nome broker;
quantità del frammento.


Esempio:

●━━ Lotto 17/02/2025 · [Directa] Directa · 2 ━━━━━━━━━━━→


Se lo spazio è insufficiente, la priorità è:

1. data del lotto;
2. broker;
3. quantità;
4. testo “Lotto”.

4. Marker del primo grafico
4.1 Simboli

Il marker BUY deve diventare un triangolo rivolto verso l’alto, più distinguibile rispetto alla linea del prezzo.

BUY          ▲
SELL         ▼
TRANSFER     ◆ oppure simbolo bidirezionale
ADJUSTMENT   ■
SPLIT        │ oppure simbolo dedicato


ASCII:

Prezzo
120 ┤                                             ▲ BUY
110 ┤                                 ╭───────────●─────
100 ┤                      ▲ BUY    ╭─╯
 90 ┤               ╭──────────────╯
 80 ┤      ▲ BUY   ╭─╯
    └────────────────────────────────────────────────── tempo


I marker restano posizionati al prezzo di mercato della rispettiva data.

4.2 Legenda
▲ Acquisti
▼ Vendite
◆ Trasferimenti
■ Rettifiche
│ Split


Le categorie devono essere attive inizialmente e disattivabili tramite legenda.

5. Primo grafico — modalità assoluta e percentuale
5.1 Modalità ABS

La modalità assoluta conserva:

Prezzo di mercato
WAC dei broker
WAC cumulato, se almeno due broker detengono l’asset
marker degli eventi


Titolo:

WAC / Prezzo di mercato

5.2 Modalità %

La modalità percentuale deve conservare le serie normalizzate già presenti e aggiungere le metriche di performance.

Serie disponibili:

Rendimento del mercato
Variazione del WAC
ROI
TWRR


Normalizzazione delle serie prezzo/WAC:

NormalizedSeries(t)=Value(t)Value(t0)−1NormalizedSeries(t) = \frac{Value(t)}{Value(t_0)}-1

dove t0t_0 è il primo punto valido della serie nel range selezionato.

ASCII:

Performance %

180% ┤                                ╭──── ROI
150% ┤                       ╭────────╯
120% ┤              ╭────────╯       ╭──── TWRR
 90% ┤       ╭──────╯         ╭──────╯
 60% ┤   ╭───╯       ╭────────╯         Rendimento mercato
 20% ┤───╯ ························  Variazione WAC
  0% ┼────────────────────────────────────────────────── tempo

5.3 Visibilità iniziale

Per la prima iterazione, rendere tutte le serie disponibili e verificare attraverso screenshot la leggibilità.

Configurazione iniziale raccomandata:

Rendimento mercato   attivo
ROI                   attivo
TWRR                  attivo
Variazione WAC        attiva


Se il risultato risulta eccessivamente affollato, la Variazione WAC potrà diventare disattivata di default senza essere rimossa.

I marker devono restare disponibili anche nella modalità percentuale, con coordinata Y sulla serie normalizzata del prezzo di mercato.

6. Tabella — modello informativo completo
6.1 Colonne disponibili

Il DataTable deve rendere disponibili:

Data apertura
Direzione
Stato
Custodia
Quantità iniziale
Quantità aperta
Prezzo apertura
Valore apertura
Valore corrente
Incassi cumulati
Open Return
P&L FIFO


Definizioni:

OpeningValuei=qi0pi0OpeningValue_i=q_i^0p_i^0 CurrentValuei(t)=qiopen(t)MarketPrice(t)CurrentValue_i(t)=q_i^{open}(t)MarketPrice(t)
Quantità iniziale
→ quantità originaria del lotto.

Quantità aperta
→ quantità ancora non chiusa.

Prezzo apertura
→ prezzo unitario di apertura.

Valore apertura
→ quantità iniziale × prezzo unitario di apertura.

Valore corrente
→ quantità aperta × prezzo corrente.

Incassi cumulati
→ ricavi delle chiusure attribuite al lotto.

Open Return
→ rendimento unitario della parte ancora aperta.

P&L FIFO
→ risultato complessivo del lotto secondo la logica FIFO.

6.2 Colonne visibili di default
Data apertura
Direzione
Stato
Custodia
Quantità aperta
Prezzo apertura
Valore apertura
Valore corrente
P&L FIFO

6.3 Colonne nascoste di default
Quantità iniziale
Incassi cumulati
Open Return


Tutte rimangono attivabili tramite il selettore colonne già disponibile nel DataTable.

6.4 Selettore colonne

Il selettore deve mantenere la sovrastruttura esistente, senza creare un nuovo sistema parallelo.

Raggruppamento concettuale:

Identità
☑ Data apertura
☑ Direzione
☑ Stato
☑ Custodia

Quantità e costo
☐ Quantità iniziale
☑ Quantità aperta
☑ Prezzo apertura
☑ Valore apertura

Risultati
☑ Valore corrente
☐ Incassi cumulati
☐ Open Return
☑ P&L FIFO

7. Modale Dettaglio lotto
7.1 Nuova semantica

La modale non deve essere considerata esclusivamente una modale di custodia.

Deve essere una modale sempre disponibile:

Dettaglio lotto


La custodia rappresenta una delle sezioni interne.

7.2 Accesso tramite context menu

La tabella deve offrire nel menu contestuale della riga:

Visualizza dettaglio lotto
Vai al lotto nel Gantt
Vai alla transazione di apertura
Copia identificativo lotto


L’azione Visualizza dettaglio lotto deve essere disponibile per:

lotto con un solo broker;
lotto senza transfer;
lotto con sole BUY;
lotto parzialmente chiuso;
lotto chiuso;
lotto LONG;
lotto SHORT.


Il click sulla cella Custodia continua ad aprire la stessa modale.

7.3 Contenuto
┌──────────────────────────────────────────────────────────────────┐
│ Dettaglio lotto — 17/02/2025                                [X] │
├──────────────────────────────────────────────────────────────────┤
│ RIEPILOGO                                                        │
│ Direzione                  LONG                                  │
│ Stato                      Aperto                                │
│ Quantità iniziale          2                                     │
│ Quantità aperta            2                                     │
│ Prezzo apertura            54,98 €                               │
│ Valore apertura           109,96 €                               │
│ Valore corrente           231,54 €                               │
│ Incassi cumulati            0,00 €                               │
│ Open Return              +110,57%                                │
│ P&L FIFO                  +121,58 €                               │
├──────────────────────────────────────────────────────────────────┤
│ CUSTODIA                                                         │
│ [Directa] Directa          2 · dal 17/02/2025                    │
├──────────────────────────────────────────────────────────────────┤
│ CRONOLOGIA                                                       │
│ 17/02/2025  ▲ BUY          +2 @ 54,98 €                          │
├──────────────────────────────────────────────────────────────────┤
│ [Vai alla transazione]                                  [Chiudi] │
└──────────────────────────────────────────────────────────────────┘

8. Grafico Valore — separazione tra selezione e presentazione
8.1 Principio

La tabella determina:

quali lotti partecipano al grafico.


Il grafico determina:

come rappresentare i lotti selezionati.


Non devono esistere checkbox custom nel grafico che duplicano la selezione della tabella.

8.2 Modalità di presentazione

Quando la metrica principale è Valore, aggiungere un selettore:

[Aggregato] [Per lotto] [Entrambi]


Il controllo deve riutilizzare lo stesso pattern visuale del selettore Attivi/Inattivi presente in Asset Global:

<div class="inline-flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
  <button>Aggregato</button>
  <button>Per lotto</button>
  <button>Entrambi</button>
</div>


Non occorre copiare letteralmente il componente se esiste un toggle segmentato riutilizzabile; occorre però mantenere:

forma compatta inline;
bordi condivisi;
aria-pressed;
colori distinti per stato attivo;
test ID specifici;
compatibilità dark mode.

Test ID consigliati:

lots-value-presentation-filter
lots-value-aggregate-toggle
lots-value-individual-toggle
lots-value-both-toggle

8.3 Aggregato

È la vista predefinita.

Mostra:

Valore aperto aggregato
Incassi cumulati aggregati
Valore complessivo aggregato
Valore di apertura complessivo

OpenValueL(t)=∑i∈LOpenValuei(t)OpenValue_{\mathcal L}(t) = \sum_{i\in\mathcal L}OpenValue_i(t) ProceedsL(t)=∑i∈LProceedsi(t)Proceeds_{\mathcal L}(t) = \sum_{i\in\mathcal L}Proceeds_i(t) TotalValueL(t)=OpenValueL(t)+ProceedsL(t)TotalValue_{\mathcal L}(t) = OpenValue_{\mathcal L}(t) + Proceeds_{\mathcal L}(t) OpeningValueL=∑i∈Lqi0pi0OpeningValue_{\mathcal L} = \sum_{i\in\mathcal L}q_i^0p_i^0

ASCII:

Valore aggregato della selezione

500 € ┤                                  ╭──── Valore complessivo
450 € ┤                            ██████╯  Incassi cumulati
400 € ┤                      ▓▓▓▓▓▓▓▓▓▓▓▓  Valore aperto
350 € ┤               ▓▓▓▓▓▓▓▓▓
300 € ┼──────── Valore di apertura complessivo ────────────────
  0 € ┼──────────────────────────────────────────────────────── tempo


Legenda:

■ Valore aperto
■ Incassi cumulati
─ Valore complessivo
─ Valore di apertura

8.4 Per lotto

Mostra una linea per ogni lotto selezionato:

Total Value — Lotto 01/04/2025
Total Value — Lotto 02/06/2025
Total Value — Lotto 01/07/2025

Valore per lotto

500 € ┤                                  ╭── Lotto 01/04
400 € ┤                         ╭────────╯
300 € ┤              ╭─────────╯   ╭──── Lotto 02/06
200 € ┤        ╭─────╯        ╭────╯
100 € ┤    ╭───╯       ╭──────╯  ╭──── Lotto 01/07
  0 € ┼────●───────────●──────────●────────────────── tempo


Non mostra le aree aggregate.

8.5 Entrambi

Mostra contemporaneamente:

area aggregata;
linea del valore complessivo aggregato;
linee Total Value dei singoli lotti.


Serve a confrontare il contributo individuale con il totale selezionato.

Valore aggregato + lotti

500 € ┤                         ╭──── Totale selezione
450 € ┤                   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
350 € ┤              ╭──── Lotto A
250 € ┤        ╭─────╯       ╭──── Lotto B
150 € ┤   ╭────╯        ╭────╯
  0 € ┼───●─────────────●────────────────────────── tempo


La prima implementazione deve produrre screenshot delle tre modalità prima di stabilire se Entrambi sia sufficientemente leggibile.

9. Legenda del grafico Valore

La legenda non determina quali lotti entrano nella selezione.

Aggregato
Valore aperto
Incassi cumulati
Valore complessivo
Valore di apertura

Per lotto
Lotto 01/04/2025
Lotto 02/06/2025
Lotto 01/07/2025

Entrambi

Contiene metriche aggregate e linee individuali, ma senza checkbox custom duplicate sopra il grafico.

Il comportamento standard ECharts hide/show può restare disponibile come controllo puramente visuale e temporaneo.

10. Grafico Rendimento

La tabella continua a determinare i lotti inclusi.

Serie principali:

Total Return di ogni lotto selezionato
Total Return aggregato opzionale


L’Open Return resta disponibile:

tooltip;
modale;
colonna opzionale della tabella.


Non inserire ROI o TWRR nel grafico dei lotti: tali metriche appartengono alla posizione aggregata e devono essere mostrate nella modalità % del primo grafico.

11. Grafico Prezzo

Titolo più esplicito:

Prezzo dei lotti selezionati


Serie:

Prezzo di mercato
Prezzo di apertura dei lotti selezionati
WAC del broker
WAC cumulato, solo quando applicabile


La selezione della tabella governa i prezzi di apertura mostrati.

12. Correzione hover
Problema

La linea del valore complessivo scompare quando il mouse entra nel grafico.

Comportamento desiderato
serie puntata:
- lineWidth incrementato;
- z-index superiore.

altre serie:
- opacità invariata;
- nessun blur;
- nessuna scomparsa.


Verificare ed eventualmente disabilitare:

emphasis.focus
blurScope
blur opacity
legend inactive opacity
areaStyle emphasis


Il tooltip non deve modificare la leggibilità complessiva del grafico.

Questo requisito vale per:

modalità Aggregato;
modalità Per lotto;
modalità Entrambi;
Rendimento;
Prezzo.

13. Piano operativo
Fase 1 — Gantt
Rimuovere la colonna HTML fissa.
Portare tutte le label nella custom series ECharts.
Rimuovere l’icona asset ripetuta.
Mostrare anno nella data del lotto.
Allineare esattamente grid.left/right col grafico WAC.
Verificare zoom, pan, clipping e tooltip.
Conservare selezione, doppio click e pulse.
Fase 2 — Primo grafico
Cambiare BUY da cerchio a triangolo verso l’alto.
Verificare coerenza degli altri simboli.
Mantenere ABS invariato.
Estendere % con:
rendimento mercato;
variazione WAC;
ROI;
TWRR.
Mantenere marker e tooltip.
Verificare leggibilità con tutte le serie attive.
Fase 3 — Tabella e modale
Aggiungere tutte le colonne previste.
Configurare il subset visibile di default.
Collegare le altre al selettore colonne.
Rinominare la modale in Dettaglio lotto.
Aggiungere context menu sulla riga.
Rendere la modale sempre accessibile.
Verificare LONG, SHORT, aperto, chiuso e senza transfer.
Fase 4 — Grafico Valore
Rimuovere i checkbox custom duplicati dei lotti.
Aggiungere il selettore segmentato:
[Aggregato] [Per lotto] [Entrambi]

Riutilizzare il pattern grafico e accessibile Attivi/Inattivi di Asset Global.
Impostare Aggregato come default.
Rendere esplicite le quattro metriche aggregate.
Implementare la vista Per lotto.
Implementare la vista Entrambi.
Correggere il bug hover/emphasis.
Produrre screenshot comparativi delle tre modalità.
Fase 5 — Rendimento e Prezzo
Eliminare selettori duplicati dei lotti.
Mantenere Total Return per ciascun lotto.
Valutare una linea aggregata opzionale.
Rinominare Prezzo in Prezzo dei lotti selezionati.
Conservare WAC broker/cumulato condizionale.
Correggere eventuali comportamenti hover analoghi.
14. Test richiesti
Gantt senza colonna fissa;
allineamento asse X WAC/Gantt;
label che scorre col pan;
segmento precedente al range;
segmento corto;
data completa con anno;
nessuna icona asset ripetuta;
marker BUY triangolare;
modalità % con quattro metriche;
colonne DataTable attive e inattive;
context menu dettaglio lotto;
modale per lotto senza transfer;
Valore Aggregato;
Valore Per lotto;
Valore Entrambi;
nessuna serie che scompare all’hover;
selezione tabella come unica fonte dei lotti;
Rendimento e Prezzo senza selezione duplicata;
dark mode;
mobile.


Test ID minimi:

lots-value-presentation-filter
lots-value-aggregate-toggle
lots-value-individual-toggle
lots-value-both-toggle
lot-row-context-menu
lot-view-details-action

15. Stato finale desiderato
┌─────────────────────────────────────────────────────────────────────┐
│ WAC / Prezzo                                [ABS] [%]               │
│ ABS → mercato, WAC, marker                                          │
│ %   → mercato, WAC, ROI, TWRR                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Vita e custodia                         [Aperti] [Tutti]            │
│                                                                     │
│ ●━━ Lotto 17/02/2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━→    │
│    ●━━ Lotto 04/03/2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━→     │
│         ●━━ Lotto 01/04/2025 · Directa · 1 ━━━━━━━━━━━━━━━━━→      │
├─────────────────────────────────────────────────────────────────────┤
│ Tabella lotti                                                       │
│ selezione · quantità · costo · valore · incassi · rendimento       │
│ context menu → Dettaglio lotto                                     │
├─────────────────────────────────────────────────────────────────────┤
│ Lotti selezionati                  [Valore] [Rendimento] [Prezzo]  │
│                                                                     │
│ Valore: [Aggregato] [Per lotto] [Entrambi]                         │
│                                                                     │
│ nessuna duplicazione della selezione                               │
└─────────────────────────────────────────────────────────────────────┘


Questo piano conserva il lavoro già completato e concentra il prossimo intervento sulla semantica visuale: un solo asse temporale coerente, una sola fonte di selezione, metriche chiaramente nominate e dettaglio del lotto sempre accessibile.
