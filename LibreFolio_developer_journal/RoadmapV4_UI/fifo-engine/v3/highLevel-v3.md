FIFO UI v3 — Piano ad alto livello
1. Obiettivo

Completare l’analisi FIFO trasformandola in una rappresentazione:

temporalmente compatta;
economicamente completa;
coerente tra Gantt, tabella e grafici;
capace di attribuire ai lotti anche dividendi e interessi;
utilizzabile anche quando il prezzo corrente non è disponibile.

Il calcolo continua a essere ricostruito dalla storia completa delle transazioni. Il periodo selezionato limita esclusivamente la visualizzazione.

2. Problemi attuali
2.1 Gantt

Lo stato attuale presenta:

eccessivo spazio verticale tra i lotti;
una riga completa per ogni branch, anche prima della sua effettiva nascita;
asse temporale visibile soltanto in fondo;
simbolo iniziale non coerente col tipo di evento;
assenza degli eventi successivi sulla vita del lotto;
highlight della selezione non aggiornato immediatamente;
tooltip con informazioni economiche insufficienti.
2.2 Tabella

Lo stato attuale presenta:

selettore colonne non funzionante;
ricerca globale ridondante rispetto ai filtri per colonna;
assenza della colonna Azioni;
ordine delle colonne non centrato sui risultati;
nessun riepilogo aggregato delle righe selezionate o visibili;
dettaglio lotto non direttamente accessibile tramite azione visibile.
2.3 Grafici

I grafici temporali sono analiticamente utili, ma non forniscono una lettura immediata di quali lotti abbiano prodotto i risultati migliori o peggiori.

Inoltre:

la selezione vuota non equivale ancora chiaramente a “tutti i lotti visibili”;
alcune serie presentano instabilità visuali;
dividendi e interessi non alimentano correttamente valore e rendimento dei lotti;
gli eventi di provento non sono evidenziati graficamente.
2.4 P&L incompleto

Il P&L dei lotti considera attualmente soprattutto:

variazione del prezzo;
vendite;
quantità residua.

Non attribuisce invece ai lotti:

dividendi;
interessi;
altri proventi associati esplicitamente all’asset.

Di conseguenza, asset come crowdfunding o prestiti possono apparire privi di rendimento nonostante abbiano generato incassi.

3. Gantt a tendere
3.1 Lane compatte

I lotti senza biforcazioni devono essere disposti verticalmente con distanza minima:

▲━━ Lotto 17 feb 2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━━━→
   ▲━━ Lotto 3 mar 2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━→
      ▲━━ Lotto 1 apr 2025 · Directa · 2 ━━━━━━━━━━━━━━━━━━━→
         ▲━━ Lotto 2 mag 2025 · Directa · 3 ━━━━━━━━━━━━━━━→


Indicativamente:

altezza lane       26–30 px
gap verticale       3–5 px


La selezione evidenzia la barra, non l’intera fascia della lane.

3.2 Branch gerarchici

Una riga figlia deve comparire soltanto nel momento in cui nasce una biforcazione.

Prima del transfer

▲━━ Lotto BTC · Coinbase · 0,15 ━━━━━━━━━━━━━━━◆

Dopo il transfer

▲━━ Lotto BTC · Coinbase · 0,15 ━━━━━━━━━━━━━━━◆
                                                ├━━ Coinbase · 0,05 ━→
                                                └══ Transito · 0,10 ═◆━━ IBKR · 0,10 ━→


Prima della biforcazione, la riga figlia resta inesistente, non una lane vuota.

3.3 Eventi sulla barra

Ogni evento deve essere rappresentato nella data in cui modifica il lotto:

BUY                  ▲
SELL                 ▼
TRANSFER              ◆
ADJUSTMENT positivo   +
ADJUSTMENT negativo   ×
SPLIT                 │


Esempio di vendita parziale:

▲━━ Lotto · 10 ━━━━━━━━━━━━━━━━━━━▼━━ Lotto · 6 ━━━━━━━━━━━━━→
                                  SELL 4


Il cambio di spessore dopo il marker rende evidente la quantità consumata.

3.4 Asse temporale sticky

L’asse X deve rimanere visibile durante lo scroll verticale del Gantt:

┌──────────────────────────────────────────────────────────────┐
│ ▲━━ Lotto A ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→  │
│    ▲━━ Lotto B ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→   │
│       ▲━━ Lotto C ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ set        gen        apr        lug               ← sticky │
└──────────────────────────────────────────────────────────────┘


L’asse sticky deve condividere con il primo grafico:

intervallo temporale;
zoom;
pan;
tick;
formatter;
margini laterali.
3.5 Tooltip del lotto

Il tooltip deve mostrare almeno:

Lotto 17/02/2025

Apertura
Tipo                         BUY
Direzione                    LONG
Broker                       Directa

Dimensione
Quantità iniziale            2
Quantità aperta              2
Prezzo apertura              42,26 €
Valore apertura              84,51 €

Situazione corrente
Prezzo corrente              50,03 €
Valore corrente             100,06 €
Incassi da vendite            0,00 €
Dividendi e interessi         4,20 €

Risultato
P&L da prezzo                +15,55 €
P&L complessivo             +19,75 €
Open Return                 +18,40%
Total Return                +23,37%

4. Selezione

Lo stato iniziale non contiene una selezione esplicita:

selectedLotIds = []


Ai fini delle analisi:

nessuna selezione
→ tutti i lotti visibili;

selezione esplicita
→ soltanto i lotti selezionati.


La selezione deve aggiornare immediatamente:

Gantt;
vista a bolle;
grafici Valore, Rendimento e Prezzo;
footer della tabella.

Non deve essere necessario applicare zoom o resize per aggiornare l’highlight.

5. Vista Timeline e vista Performance

Il blocco attuale diventa:

Vita e custodia dei lotti

[Timeline] [Performance]

Timeline

Contiene il Gantt compatto e gerarchico.

Performance

Contiene una vista a bolle dei lotti LONG, con due modalità:

[ABS] [%]

6. Vista a bolle
6.1 Coordinata orizzontale

La bolla resta sempre sulla data di apertura:

xi=OpeningDateix_i=OpeningDate_i

Vendite, dividendi, interessi, split e transfer non modificano la coordinata X.

6.2 Modalità ABS

La coordinata verticale rappresenta il P&L complessivo in target currency:

yi=TotalPnLiy_i=TotalPnL_i
P&L €

+500 ┤                         ● Lotto A
     ┤                         ╎
+250 ┤          ● Lotto B     ╎
     ┤          ╎             ╎
   0 ┼────▲─────▲─────────────▲──────────────── data apertura
     ┤
-300 ┤                                 ╎
     ┤                                 ● Lotto C


La linea verticale:

verde    P&L positivo
rossa    P&L negativo
neutra   P&L prossimo a zero

6.3 Modalità percentuale

La coordinata verticale rappresenta il Total Return:

yi=TotalPnLiOpeningValueiy_i= \frac{TotalPnL_i}{OpeningValue_i}
Total Return

+80% ┤                         ● Lotto A
     ┤                         ╎
+35% ┤          ● Lotto B     ╎
  0% ┼────▲─────▲─────────────▲──────────────── data apertura
-35% ┤                                 ╎
     ┤                                 ● Lotto C


Un lotto completamente chiuso conserva il proprio risultato finale.

Un lotto aperto continua a variare con:

prezzo corrente;
vendite parziali;
dividendi;
interessi.
6.4 Vendite parziali

La parte venduta diventa fissa al momento della chiusura. La parte residua continua a variare.

TotalPnLi(t)=RealizedPnLi+OpenPnLi(t)+Incomei(t)TotalPnL_i(t)= RealizedPnL_i+ OpenPnL_i(t)+ Income_i(t)

I transfer sono economicamente neutrali.

6.5 Dimensione e colore
dimensione bolla → valore di apertura
colore verde     → risultato positivo
colore rosso     → risultato negativo
colore neutro    → risultato prossimo a zero


Il broker viene mostrato mediante bordo, icona o tooltip.

7. Dividendi e interessi asset-linked
7.1 Attribuzione

Le transazioni:

DIVIDEND con asset_id
INTEREST con asset_id


devono essere allocate ai lotti LONG aperti dell’asset alla data della transazione.

L’Asset Event collegato è informativo e non determina la data di attribuzione.

AllocationDate=TransactionDateAllocationDate=TransactionDate
7.2 Ripartizione proporzionale

Per ogni lotto aperto:

wi(t)=qiopen(t)∑jqjopen(t)w_i(t)= \frac{q_i^{open}(t)} {\sum_j q_j^{open}(t)} AllocatedIncomei(t)=IncomeTotal(t)⋅wi(t)AllocatedIncome_i(t)= IncomeTotal(t)\cdot w_i(t)

Deve essere garantita la conservazione:

∑iAllocatedIncomei(t)=IncomeTotal(t)\sum_i AllocatedIncome_i(t)=IncomeTotal(t)

Gli eventuali residui da arrotondamento devono essere assegnati deterministicamente.

7.3 Effetti

I proventi alimentano:

P&L complessivo;
Total Return;
Cash Yield;
tabella;
footer;
tooltip;
modale;
grafico Valore;
grafico Rendimento;
vista a bolle.

Non modificano:

quantità;
custodia;
prezzo di apertura;
WAC;
ordine FIFO.
8. Proventi nei grafici

Dividendi e interessi devono essere evidenziati con linee verticali tratteggiate:

DIVIDEND   tratteggio verde/teal
INTEREST   tratteggio blu/viola

Primo grafico
Prezzo / Performance

120 ┤                       ╭─────────────
100 ┤              ╭────────╯
 80 ┤     ╭────────╯
    └─────┼─────────────┼──────────────── tempo
          ┆             ┆
      Dividendo      Interesse

Grafico Valore

Nella data del provento:

Valore residuo      invariato
Proventi cumulati   aumentano
Valore complessivo  aumenta

Grafico Rendimento

Il Total Return aumenta nella data del provento.

La bolla resta invece sulla data di apertura e si sposta soltanto verticalmente.

9. Valore corrente mancante

Se il prezzo corrente non è disponibile, per qualsiasi asset:

EstimatedOpenValuei=OpenQuantityi⋅AdjustedOpeningUnitPriceiEstimatedOpenValue_i= OpenQuantity_i\cdot AdjustedOpeningUnitPrice_i

Pertanto:

OpenPnLi=0OpenPnL_i=0

fino alla disponibilità di un prezzo attendibile.

Il risultato può comunque includere:

vendite;
dividendi;
interessi;
adjustment.

La UI deve distinguere:

valore di mercato
valore stimato al costo


Il valore stimato deve usare:

stile neutro o tratteggiato;
tooltip esplicativo;
Data Quality issue dedicata.
10. Interessi e dividendi senza asset

Se una transazione DIVIDEND o INTEREST non ha asset_id, non deve essere allocata ai lotti.

Deve comparire negli:

Altri effetti del periodo


Esempio:

Descrizione                         Categoria   P&L Periodo   Broker
Interessi non allocati — Recrowd   Provento    +850,00 €    Recrowd
Costi non allocati — Recrowd       Costo       -554,16 €    Recrowd


Regola:

DIVIDEND/INTEREST con asset
→ provento allocato ai lotti.

DIVIDEND/INTEREST senza asset
→ provento non allocato del broker.

FEE/TAX senza asset
→ costo non allocato del broker.

11. Tabella unificata
11.1 Rimozioni e correzioni
rimuovere la ricerca globale;
correggere il selettore colonne;
aggiungere la colonna Azioni;
mantenere filtri e ordinamento per colonna.
11.2 Ordine orientato ai risultati

Ordine consigliato:

Selezione
Data apertura
P&L complessivo
Total Return
Proventi
Valore corrente
Quantità aperta
Custodia
Stato
Prezzo apertura
Valore apertura
Quantità iniziale
Open Return
Direzione
Azioni


Colonne visibili di default:

Data apertura
P&L complessivo
Total Return
Proventi
Valore corrente
Quantità aperta
Custodia
Azioni


Colonne condizionali:

Stato
→ nascosta se tutti i lotti hanno lo stesso stato.

Direzione
→ nascosta se tutti i lotti sono LONG.

Proventi
→ nascosta se tutti i valori sono nulli.


Le altre colonne restano disponibili nel selettore.

11.3 Footer

Il footer usa:

righe selezionate, se esistono;
altrimenti tutte le righe visibili.


Aggregazioni:

P&L complessivo    somma
Proventi           somma
Valore corrente    somma
Quantità aperta    somma
Prezzo apertura    media ponderata
Total Return       P&L totale / valore apertura totale
Open Return        media ponderata sul valore aperto

12. Azioni e dettaglio lotto

Il context menu esistente viene mantenuto:

Visualizza dettaglio lotto
Vai al lotto nel Gantt
Vai alla transazione di apertura
Copia identificativo lotto


La tabella deve avere anche una colonna finale:

⋮


che apre lo stesso menu.

L’identificativo lotto va descritto come:

Identificativo tecnico stabile derivato dalla transazione di apertura, utilizzato per audit, supporto e correlazione API.

13. Navigazione alla transazione

Vai alla transazione di apertura deve:

navigare alla pagina Transazioni;
raggiungere la riga corretta;
aprire la Transaction Modal in modalità lettura;
alla chiusura, centrare la riga;
applicare un pulse evidente.

Il tasto Indietro deve preservare:

dashboard;
tab;
asset;
range;
analisi lotti;
selezione.
14. Range temporale

Il calcolo deve partire sempre dalla prima transazione dell’asset:

CalculationStart=min⁡(transaction.date)CalculationStart= \min(transaction.date)

Il periodo selezionato limita soltanto il rendering.

Quando date_from non è esplicitata:

datefrom=CalculationStartdate_{from}=CalculationStart

Il valore Tutti non deve partire dal primo prezzo nello storico, ma dalla prima operazione associata all’asset.

15. Stato finale desiderato
┌───────────────────────────────────────────────────────────────┐
│ PMC / Prezzo / Performance                                   │
│ marker transazioni + marker dividendi/interessi              │
├───────────────────────────────────────────────────────────────┤
│ Vita e custodia                         [Timeline][Performance]│
│                                                               │
│ Timeline:                                                     │
│ ▲━━ Lotto A ━━━━━━━━━▼━━ Lotto A residuo ━━━━━━━━━━━━━━━→    │
│    ▲━━ Lotto B ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→    │
│                                                               │
│ Performance:                       [ABS][%]                    │
│ bolle sulla data di apertura, altezza = risultato            │
├───────────────────────────────────────────────────────────────┤
│ Tabella lotti                                                 │
│ risultati · valore · proventi · quantità · custodia · azioni │
│ footer aggregato                                              │
├───────────────────────────────────────────────────────────────┤
│ Grafici dei lotti                                             │
│ Valore e Return includono dividendi/interessi                │
└───────────────────────────────────────────────────────────────┘


Questo piano definisce lo stato a tendere senza vincolare prematuramente i dettagli implementativi: la priorità è rendere la performance dei lotti economicamente completa, temporalmente leggibile e immediatamente confrontabile.
