FIFO Lot Engine v2 — Piano di rifinitura visuale e funzionale
1. Obiettivo

Il backend, il nuovo FifoLotEngine, l’endpoint bulk e le principali interazioni sono stati implementati. La struttura dati non deve essere riprogettata senza prima dimostrare un’insufficienza del contratto API.

Questa fase deve correggere la distanza tra:

semantica temporale definita nel piano;
dati prodotti dal backend;
visualizzazione attualmente implementata.

L’obiettivo non è aggiungere nuove funzionalità, ma rendere leggibili e coerenti quelle già previste.

2. Stato attuale e problemi osservati
2.1 WAC e prezzo di mercato
Stato attuale

Il grafico mostra correttamente:

Prezzo di mercato
WAC del broker
asse temporale
toggle ABS / %

Problema

Mancano i marker delle transazioni che spiegano l’evoluzione della posizione e del WAC:

BUY
SELL
TRANSFER
ADJUSTMENT
SPLIT

Stato desiderato
WAC / Prezzo di mercato

75 ┤                                             ╭──── Prezzo di mercato
72 ┤                                         ╭───╯
69 ┤                         ◆ SELL      ╭────╯
66 ┤               ● BUY   ╭────────────╯
63 ┤      ● BUY  ┌─────────┘
60 ┤─────────────┘ WAC Directa
   └──────────────────────────────────────────────────────────── tempo
          set       ott       nov       dic       gen       ...


I marker devono essere posizionati:

x = data della transazione
y = prezzo di mercato dell’asset nella stessa data


Se il prezzo esatto non è disponibile:

ultimo prezzo precedente


Se nessun prezzo precedente è disponibile:

marker non posizionabile
DataQuality issue non bloccante

2.2 Gantt dei lotti
Stato attuale

Il componente mostra:

una riga per lotto;
intestazione e broker;
righe orizzontali;
asse temporale soltanto in fondo;
nessun segmento temporale leggibile;
lane vuote;
nessun tooltip;
selezione/doppio click parzialmente funzionanti.

La visualizzazione corrente equivale a una lista verticale, non a un Gantt.

Lotto 01/09
1 set 2025 · Directa
────────────────────────────────────────

Lotto 01/10
1 ott 2025 · Directa
────────────────────────────────────────

Stato desiderato

Anche in presenza di sole BUY, ogni lotto deve avere un segmento che parte dalla data di apertura e prosegue fino a:

data di chiusura
oppure date_to, se ancora aperto


La label deve essere inserita nel segmento, in modo da lasciare l’asse X perfettamente allineato al grafico WAC.

Vita e custodia dei lotti

       set          ott          nov          dic          gen          ...

       ●━━ Lotto 01/09 · Directa · 3 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
                    ●━━ Lotto 01/10 · Directa · 2 ━━━━━━━━━━━━━━━━━━→
                         ●━━ Lotto 08/10 · Directa · 3 ━━━━━━━━━━━━━→
                                      ●━━ Lotto 03/11 · Directa · 3 → 
                                                 ●━━ Lotto 08/12 · 3 →


Il Gantt deve mostrare una vera coordinata temporale:

inizio segmento = data di apertura/cambio custodia
fine segmento   = evento successivo, chiusura o date_to

2.3 Grafico comparativo dei lotti selezionati
Stato attuale
Valore

Mostra una barra categoriale per lotto, quindi una fotografia corrente:

Lotto 01/10  █
Lotto 08/10  █
Lotto 03/11  █


Non mostra l’evoluzione temporale.

Rendimento

Mostra:

Nessun dato disponibile


anche per normali lotti BUY con prezzo di apertura noto.

Prezzo

Mostra una variante del primo grafico, ma:

include WAC cumulato anche con un solo broker;
mostra label generiche come WAC broker #1;
non rende chiara la differenza rispetto al grafico aggregato superiore.
Stato desiderato

Tutte e tre le modalità devono avere:

asse X = tempo
serie = lotti selezionati
range iniziale = range globale selezionato

3. Principi di visualizzazione
3.1 Asse temporale

I grafici seguenti devono essere temporali:

WAC / Prezzo di mercato
Gantt
Valore dei lotti
Rendimento dei lotti
Prezzo dei lotti


WAC e Gantt devono condividere sempre:

date_from
date_to
zoom
pan
crosshair


Il grafico comparativo utilizza inizialmente lo stesso range, ma mantiene zoom indipendente.

3.2 Assenza di eventi complessi

Un asset con sole BUY non deve produrre una visualizzazione vuota.

BUY
→ apertura della barra Gantt
→ serie Valore
→ serie Rendimento
→ linea del prezzo di apertura


SELL, transfer, adjustment e split arricchiscono la storia, ma non sono necessari affinché i grafici funzionino.

3.3 Dati mancanti

Prima di cambiare il rendering, occorre distinguere:

dato assente dal backend
dato non richiesto dal frontend
dato presente ma mappato male
dato presente ma filtrato erroneamente
dato non renderizzato da ECharts


Ogni correzione deve partire dall’ispezione della response reale di:

POST /portfolio/lots/analysis

4. Rifinitura del Gantt
4.1 Modello di rendering

Ogni lotto occupa una lane.

Ogni intervallo continuo di custodia produce un segmento.

Lane
└─ uno o più custody segments


Caso semplice:

●━━ Lotto 01/10 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→


Caso chiuso:

●━━ Lotto 01/10 · Directa · 2 ━━━━━━━━━━━━━◆
                                              SELL completa


Caso di vendita parziale:

●━━ Directa · 10 ━━━━━━━━━━━◆━━ Directa · 6 ━━━━━━━━━━━━━━━→
                             SELL 4


Caso di transfer parziale:

                           ┌━━ Coinbase · 0,05 ━━━━━━━━━━━━━→
●━━ Coinbase · 0,15 ━━━━━━┤
                           └══ In transito · 0,10 ══ IBKR ━→

4.2 Spessore

Lo spessore rappresenta la quantità, normalizzata rispetto al lotto con quantità originaria massima dello stesso asset.

Qmax⁡=max⁡iqi0Q_{\max}=\max_i q_i^0 Thickness(q)=Tmin⁡+qQmax⁡(Tmax⁡−Tmin⁡)Thickness(q)=T_{\min}+ \frac{q}{Q_{\max}}(T_{\max}-T_{\min})
Quantità massima  ━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quantità media    ━━━━━━━━━━━━━━━━━
Quantità minima   ━━━━━
Quantità zero     assente


Lo spessore non deve dipendere dal valore di mercato.

4.3 Colore, pattern e opacità
colore       = broker
tratteggio   = in transito
opacità      = stato
bordo/glow   = selezione


Scala fissa:

ramo aperto       90%
in transito       65% + pattern
ramo chiuso       45%
fuori dal range   assente


La selezione non deve cambiare l’opacità degli altri segmenti.

4.4 Range
Aperto prima del range
←━━ Directa · 3 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→

Aperto dentro il range
          ●━━ Directa · 3 ━━━━━━━━━━━━━━━━━━━━━━━━━━━→

Chiuso dentro il range
          ●━━ Directa · 3 ━━━━━━━━━◆

Interamente fuori dal range
nessuna lane
nessun separatore
nessuno spazio vuoto


Questo requisito deve eliminare le linee vuote attualmente visibili.

4.5 Tooltip
Hover su ramo aperto
Lotto aperto il 1 ottobre 2025

Direzione              LONG
Broker                  Directa
Dal                     1 ottobre 2025
Quantità originaria     2
Quantità nel ramo       2
Prezzo di apertura      61,81 €
Valore corrente         142,40 €
Open Return             +15,19%
P&L FIFO                +18,86 €
Stato                   Aperto

Hover sul transito
In transito

Da                      Coinbase
A                       Interactive Brokers
Quantità                0,10 BTC
Inizio                  6 luglio 2026
Fine                    8 luglio 2026

Interazioni
hover
→ tooltip

click
→ selezione/deselezione del lotto

doppio click
→ selezione
→ scroll alla riga della tabella
→ pulse temporaneo


Non è previsto un infobox persistente sul Gantt.

5. Marker nel grafico WAC
5.1 Tipi
BUY          ● cerchio
SELL         ◆ rombo
TRANSFER     ⇄ doppia freccia o simbolo dedicato
ADJUSTMENT   ■ quadrato
SPLIT        │ marker verticale con icona dedicata

5.2 Posizionamento
x=transaction.datex=transaction.date y=MarketPrice(transaction.date)y=MarketPrice(transaction.date)

I marker non devono essere posizionati sul WAC, perché la coordinata verticale deve rappresentare un prezzo direttamente confrontabile col mercato.

5.3 Tooltip
8 ottobre 2025

Acquisto
Broker                  Directa
Quantità                3
Ammontare               -185,40 €
Prezzo unitario         61,80 €
Prezzo di mercato       61,90 €
WAC dopo l’operazione   61,20 €


Per transfer:

Trasferimento

Da                      Coinbase
A                       Interactive Brokers
Quantità                0,10 BTC
Intervallo transito     6–8 luglio 2026


Per split:

Split 2:1

Quantità precedente     10
Quantità successiva     20
WAC precedente          100,00 €
WAC successivo           50,00 €
Costo totale            invariato

5.4 Visibilità

Tutti i marker devono essere visibili inizialmente.

La legenda deve consentire di nascondere:

Acquisti
Vendite
Trasferimenti
Rettifiche
Split


Se un marker coincide con un altro nella stessa data, devono essere applicati:

offset verticale
oppure raggruppamento con count e tooltip espanso

6. Tabella unificata
6.1 Colonne

La tabella deve mostrare:

Selezione
Data apertura
Direzione
Stato
Custodia
Quantità aperta
Prezzo apertura
Valore corrente
P&L FIFO


ASCII:

┌───┬────────────┬───────┬──────────┬────────────┬────────┬──────────┬──────────┬──────────┐
│   │ Apertura   │ Dir.  │ Stato    │ Custodia   │ Q.tà   │ Prezzo   │ Valore   │ P&L FIFO │
├───┼────────────┼───────┼──────────┼────────────┼────────┼──────────┼──────────┼──────────┤
│ ☑ │ 01/10/2025 │ LONG  │ Aperto   │ Directa ›  │ 2      │ 61,80 €  │ 142,40 € │ +18,86 € │
│ ☑ │ 08/10/2025 │ LONG  │ Aperto   │ Directa ›  │ 3      │ 62,10 €  │ 213,60 € │ +26,07 € │
│ ☐ │ 03/11/2025 │ LONG  │ Parziale │ 2 broker › │ 1 / 3  │ 63,00 €  │  71,20 € │ +24,96 € │
└───┴────────────┴───────┴──────────┴────────────┴────────┴──────────┴──────────┴──────────┘

6.2 Custodia

La cella deve apparire interattiva:

[broker icon] Directa  ›


oppure:

2 broker  ›


Il click apre la modale Custodia senza cambiare involontariamente la selezione della riga.

6.3 Open Return

L’Open Return non deve necessariamente occupare una colonna dedicata.

Deve comparire:

nel tooltip del Gantt;
nella modale;
eventualmente in un tooltip sulla cella P&L FIFO.

Definizione:

OpenReturni(t)=MarketPrice(t)OpeningReferencePricei−1OpenReturn_i(t)= \frac{MarketPrice(t)}{OpeningReferencePrice_i}-1

Descrive soltanto il rendimento unitario della posizione ancora aperta e non include gli incassi storici.

7. Grafico comparativo — modello comune

Tutte le modalità devono usare:

asse X = data
asse Y = metrica della modalità
serie = lotti selezionati


La selezione corrente deriva direttamente dal DataTable.

┌─────────────────────────────────────────────────────────────────────┐
│ 3 lotti selezionati                 [Valore] [Rendimento] [Prezzo] │
│                                                                     │
│ ☑ Lotto 01/10   ☑ Lotto 08/10   ☑ Lotto 03/11                    │
│                                                                     │
│                  grafico temporale                                  │
│                                                                     │
│  └──── ott ───── nov ───── dic ───── gen ───── ... ───── lug      │
└─────────────────────────────────────────────────────────────────────┘


Nessuna modalità deve utilizzare i nomi dei lotti come asse X categoriale.

8. Modalità Valore
8.1 Metriche

Per il lotto ii:

OpenValuei(t)=qiopen(t)⋅MarketPrice(t)OpenValue_i(t)=q_i^{open}(t)\cdot MarketPrice(t) Proceedsi(t)=incassi cumulati delle SELL attribuite al lottoProceeds_i(t)= \text{incassi cumulati delle SELL attribuite al lotto} TotalValuei(t)=OpenValuei(t)+Proceedsi(t)TotalValue_i(t)=OpenValue_i(t)+Proceeds_i(t) P&Li(t)=TotalValuei(t)−OriginalCostiP\&L_i(t)=TotalValue_i(t)-OriginalCost_i

Gli incassi restano attribuiti al lotto anche dopo la vendita.

8.2 Visualizzazione scelta: variante 3

La modalità deve contenere entrambe le prospettive.

Vista principale aggregata
Valore della selezione

500 € ┤                         ███████ Incassi cumulati
450 € ┤                    ████████████
400 € ┤              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  Valore residuo
350 € ┤         ▓▓▓▓▓▓▓▓▓▓
300 € ┼──────── Costo originario complessivo ───────────────────
250 € ┤    ▓▓▓▓▓▓
  0 € ┼──────────────────────────────────────────────────────────
      ott       nov       dic       gen       ...             lug


Stack:

area inferiore = valore residuo aggregato
area superiore = incassi cumulati aggregati


Linea:

costo originario complessivo

Serie individuali

Le linee dei singoli lotti devono essere disponibili tramite legenda:

Total Value — Lotto 01/10
Total Value — Lotto 08/10
Total Value — Lotto 03/11


Per evitare caos iniziale:

aggregato visibile di default
serie individuali disponibili e attivabili


La selezione dei lotti non viene limitata.

8.3 Vendita parziale

Esempio:

Costo originario       100 €
Valore prima vendita   150 €
Vendita metà            75 €
Valore residuo          75 €


Dopo la vendita:

OpenValue       = 75 €
Proceeds        = 75 €
TotalValue      = 150 €
P&L             = 50 €


La vendita non deve produrre un crollo artificiale del valore totale del lotto.

150 € ┤─────────────── Total Value ──────────────────────────
 75 € ┤          ▓▓▓▓ Valore residuo
 75 € ┤          ████ Incassi cumulati
      └──────────◆ SELL──────────────────────────────────────

9. Modalità Rendimento
9.1 Rendimento totale del lotto

La metrica principale deve includere gli incassi:

TotalReturni(t)=OpenValuei(t)+Proceedsi(t)OriginalCosti−1TotalReturn_i(t)= \frac{OpenValue_i(t)+Proceeds_i(t)} {OriginalCost_i}-1

Questa serie non dipende dalla presenza di dividendi.

Per una BUY deve essere disponibile dal giorno dell’apertura.

Rendimento totale

30% ┤                                 ╭──── Lotto 01/10
25% ┤                       ╭─────────╯
20% ┤              ╭────────╯      ╭── Lotto 08/10
15% ┤       ╭──────╯        ╭──────╯
 0% ┼───────●───────────────●──────────●──────────────────────
           1 ott           8 ott      3 nov                  tempo

9.2 Adjustment positivo

Per costo originario nullo, la percentuale deve utilizzare il prezzo di riferimento alla ricezione:

ReferencePricei=prezzo esatto o ultimo precedenteReferencePrice_i= \text{prezzo esatto o ultimo precedente} RelativeReturni(t)=MarketPrice(t)ReferencePricei−1RelativeReturn_i(t)= \frac{MarketPrice(t)}{ReferencePrice_i}-1

La serie parte da 0%0\%.

9.3 Open Return

L’Open Return resta informazione secondaria:

OpenReturni(t)=MarketPrice(t)OpeningReferencePricei−1OpenReturn_i(t)= \frac{MarketPrice(t)}{OpeningReferencePrice_i}-1

Deve comparire in:

tooltip della serie
tooltip Gantt
modale Custodia


Tooltip esempio:

Lotto 01/10 — 15 aprile 2026

Rendimento totale       +19,40%
Open Return             +15,20%
Valore residuo          142,40 €
Incassi cumulati         18,00 €
P&L FIFO                 +26,20 €

9.4 Empty state

Nessun dato disponibile è ammesso soltanto quando:

nessun lotto è selezionato;
non esiste alcun prezzo utilizzabile;
tutte le serie selezionate sono dichiarate UNAVAILABLE.

Non è ammesso per normali BUY con prezzo di apertura e storico prezzi disponibili.

10. Modalità Prezzo
10.1 Serie

Sempre:

Prezzo di mercato
Prezzo di apertura di ogni lotto selezionato


Con un solo broker:

WAC del broker
nessun WAC cumulato


Con almeno due broker che detengono l’asset:

WAC cumulato
WAC singoli disponibili in legenda

10.2 Caso a un broker
Prezzo e costo medio

75 ┤                                        ╭──── Prezzo di mercato
72 ┤                               ╭────────╯
69 ┤
66 ┼──── Prezzo apertura Lotto 08/10 ─────────────────────────────
63 ┼──── Prezzo apertura Lotto 01/10 ─────────────────────────────
62 ┤          ┌──── WAC Directa ──────────────────────────────────
   └────────────────────────────────────────────────────────────── tempo


Legenda:

Prezzo di mercato
Lotto 01/10
Lotto 08/10
WAC — Directa


Non devono comparire:

WAC cumulato
WAC broker #1

10.3 Caso multi-broker
Prezzo di mercato
Prezzi di apertura
WAC cumulato
WAC — Directa
WAC — IBKR


Visibilità iniziale:

Prezzo di mercato       attivo
Prezzi apertura         attivi
WAC cumulato            attivo
WAC singoli             disponibili in legenda

11. Filtro Aperti / Tutti
Aperti

Mostra soltanto:

lotti con quantità aperta > 0 alla data date_to

Tutti

Mostra:

lotti aperti;
lotti parzialmente chiusi;
lotti chiusi che intersecano il range visibile.


Un lotto completamente chiuso prima di date_from non deve generare:

lane;
separatore;
spazio nel Gantt.
12. Diagnostica preliminare obbligatoria

Prima delle modifiche visuali, verificare la response del bulk endpoint su un asset reale.

Dati da ispezionare
lots
custody_segments
lot_events
value_history
return_history
price_history
broker_wac_history
cumulative_wac_history
data_quality

Matrice diagnostica
Gantt vuoto
├─ custody segment assente?
├─ end_date null?
├─ data fuori range?
├─ dimension mapping errato?
├─ thickness zero?
└─ segmento disegnato ma invisibile?

Rendimento vuoto
├─ analysis non richiesta?
├─ history assente?
├─ riferimento apertura assente?
├─ valori null?
├─ filtro frontend errato?
└─ x-axis categoriale invece che temporale?

WAC cumulato scorretto
├─ count dei broker calcolato sullo scope?
├─ broker con quantità realmente aperta?
├─ serie sempre inclusa dal backend?
└─ condizione frontend mancante?


Il risultato della diagnostica deve essere annotato prima di scegliere se modificare:

backend
DTO/API
mapping frontend
solo configurazione ECharts

13. Piano operativo di rifinitura
Fase 1 — Contratto dati
Catturare una response reale del bulk endpoint.
Verificare completezza delle history.
Verificare date, quantità e end_date.
Verificare richieste requested_analyses.
Correggere backend soltanto se i dati necessari sono realmente assenti.
Aggiungere test API mirati sulle serie temporali.

Risultato atteso:

ogni BUY produce:
- lotto;
- custody segment;
- value history;
- return history;
- opening price;
- event marker.

Fase 2 — Gantt temporale
Correggere il mapping ECharts.
Renderizzare un segmento per ogni intervallo.
Usare date_to per intervalli aperti.
Eliminare lane vuote.
Inserire label nel segmento.
Applicare spessore proporzionale.
Applicare colori broker e pattern transito.
Aggiungere tooltip.
Collegare click e doppio click.
Verificare zoom condiviso col grafico WAC.

Criterio di completamento:

con sole BUY devono essere chiaramente visibili più barre
che iniziano in date differenti e terminano a date_to.

Fase 3 — Marker WAC
Integrare lot_events nel primo grafico.
Posizionare marker al prezzo di mercato del giorno.
Applicare fallback al prezzo precedente.
Aggiungere simboli per tipo evento.
Aggiungere tooltip.
Gestire eventi coincidenti.
Rendere le categorie filtrabili.
Fase 4 — Grafico comparativo temporale
Valore
Rimuovere l’asse X categoriale.
Usare daily history.
Mostrare area aggregata:
valore residuo;
incassi cumulati.
Mostrare costo originario.
Esporre le linee individuali in legenda.
Verificare continuità dopo SELL parziale.
Rendimento
Individuare perché la serie è vuota.
Renderizzare TotalReturn.
Includere gli incassi.
Gestire Adjustment+ con riferimento di mercato.
Mostrare Open Return nei tooltip.
Mostrare date sull’asse X.
Prezzo
Mostrare prezzo di mercato.
Mostrare prezzi di apertura selezionati.
Mostrare WAC broker con nome reale.
Mostrare WAC cumulato solo con almeno due broker effettivamente detentori.
Rimuovere label broker #N.
Fase 5 — Tabella e modale
Aggiungere Prezzo apertura.
Aggiungere Valore corrente.
Rinominare Quantità in Quantità aperta.
Rendere Custodia visibilmente cliccabile.
Mostrare Open Return nella modale.
Mostrare cronologia completa nella modale.
Verificare selezione multipla e mantenimento dopo refresh.
Verificare doppio click e pulse reciproco.
Fase 6 — Test e rifinitura

Test automatici o E2E mirati su:

Gantt con sole BUY
Gantt con SELL parziale
Gantt con SELL completa
Gantt con TRANSFER parziale
tooltip Gantt
click e doppio click
sync zoom WAC/Gantt
marker BUY/SELL
Valore temporale
Rendimento non vuoto
Prezzo con un broker
Prezzo con più broker
Custodia modal
Aperti/Tutti
dark mode
mobile


Validazioni:

svelte-check
./dev.py api sync
./dev.py i18n audit
./dev.py mkdocs build
pytest relevant backend/API tests

14. Stato finale desiderato
┌────────────────────────────────────────────────────────────────────┐
│ WAC / Prezzo                                                       │
│ linee temporali + marker delle transazioni                         │
├────────────────────────────────────────────────────────────────────┤
│ Gantt                                                             │
│ barre temporali reali, biforcazioni, transito e tooltip            │
├────────────────────────────────────────────────────────────────────┤
│ Tabella unificata                                                 │
│ selezione multipla + prezzo + valore + Custodia cliccabile         │
├────────────────────────────────────────────────────────────────────┤
│ Confronto selezionati                                             │
│                                                                    │
│ [Valore]      area aggregata + linee individuali                  │
│ [Rendimento]  Total Return nel tempo + Open Return in tooltip     │
│ [Prezzo]      mercato + prezzi apertura + WAC pertinenti          │
└────────────────────────────────────────────────────────────────────┘


La fase di rifinitura si considera conclusa soltanto quando tutti e tre i grafici inferiori rispondono chiaramente a una domanda:

Gantt:
quando e dove è vissuto il lotto?

Valore:
quanto valore complessivo ha prodotto?

Rendimento:
come è variato il rendimento totale dalla sua apertura?

Prezzo:
come si confrontano mercato, prezzo di apertura e costo medio?
