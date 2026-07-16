Proposta formale per un motore FIFO a segmenti in LibreFolio
1. Scopo e separazione dei domini

Si propone di introdurre un nuovo FifoLotEngine, indipendente dal Portfolio Engine aggregato attuale.

I due motori rispondono a domande differenti:

Portfolio Engine

Modello aggregato per asset e broker:

Posizionea,b(t)=(Qa,b(t),WACa,b(t),MVa,b(t),NAV(t))\text{Posizione}_{a,b}(t) = \left( Q_{a,b}(t), WAC_{a,b}(t), MV_{a,b}(t), NAV(t) \right)

dove:

aa è l’asset;
bb è il broker;
QQ è la quantità detenuta;
WACWAC è il costo medio ponderato riconosciuto;
MVMV è il valore di mercato.

Il Portfolio Engine continua a calcolare:

NAV e Book Value;
quantità aggregate;
WAC per broker e cumulato;
performance;
liquidità;
modello K/R/W;
stato in transito aggregato.
FifoLotEngine

Modello puntuale, event-sourced, finalizzato a ricostruire:

origine delle quantità;
consumo FIFO;
vendite attribuite ai lotti;
custodia per broker;
biforcazioni provocate dai trasferimenti;
incassi e P&L per lotto;
storia temporale di ogni lotto.

Il WAC non determina l’identità o il prezzo originario dei lotti FIFO.

2. Dominio matematico
2.1 Transazioni rilevanti

Per un asset aa, il motore FIFO considera esclusivamente le transazioni che ne modificano la quantità:

Ta={BUY, SELL, ADJUSTMENT, TRANSFER}\mathcal{T}_a = \{ BUY,\ SELL,\ ADJUSTMENT,\ TRANSFER \}

Le altre transazioni non modificano i lotti:

{DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, FEE, TAX, CASH_TRANSFER, FX_CONVERSION}\{ DEPOSIT,\ WITHDRAWAL,\ DIVIDEND,\ INTEREST,\ FEE,\ TAX,\ CASH\_TRANSFER,\ FX\_CONVERSION \}

Dividendi e interessi possono contribuire alla performance complessiva dell’asset, ma non appartengono alla lottizzazione FIFO.

2.2 Lotto originario

Un lotto LiL_i è una quantità di asset generata da una singola transazione di origine.

Li=(idi, ai, ti0, qi0, pi0, ci, oi)L_i = \left( id_i,\, a_i,\, t_i^0,\, q_i^0,\, p_i^0,\, c_i,\, o_i \right)

dove:

idiid_i: identificatore stabile del lotto;
aia_i: asset;
ti0t_i^0: data di origine;
qi0>0q_i^0 > 0: quantità originaria;
pi0≥0p_i^0 \ge 0: prezzo FIFO unitario originario;
cic_i: valuta originaria;
oio_i: transazione di origine.

Ogni transazione di origine crea un lotto distinto. Due BUY nella stessa data e allo stesso prezzo non vengono fuse, così da preservare auditabilità e relazione con la singola transazione.

2.3 Prezzo FIFO originario

Per una BUY con quantità qq e ammontare totale A<0A<0:

p0=∣A∣qp^0 = \frac{|A|}{q}

Esempio:

q=0,15 BTC,A=−200 EURq = 0{,}15\ BTC,\qquad A=-200\ EUR p0=2000,15=1.333,33 EUR/BTCp^0 = \frac{200}{0{,}15} = 1.333{,}33\ EUR/BTC

Il valore amount rappresenta pertanto il costo complessivo, non il prezzo unitario.

Per un ADJUSTMENT positivo:

p0=0p^0 = 0

poiché nessuna liquidità registrata nel perimetro LibreFolio è stata spesa per ottenere l’asset.

2.4 Frammento di custodia

Un lotto può essere suddiviso in più frammenti Fi,jF_{i,j}, senza perdere la propria identità.

Fi,j=(Li, bi,j, qi,j, [ti,jstart,ti,jend), si,j)F_{i,j} = \left( L_i,\, b_{i,j},\, q_{i,j},\, [t_{i,j}^{start},t_{i,j}^{end}),\, s_{i,j} \right)

dove:

LiL_i: lotto originario;
bi,jb_{i,j}: broker custode oppure stato IN_TRANSIT;
qi,j>0q_{i,j}>0: quantità del frammento;
tstartt^{start}, tendt^{end}: intervallo temporale;
si,js_{i,j}: stato del frammento.

Per ogni data tt:

qiopen(t)=∑jqi,j(t)q_i^{open}(t) = \sum_j q_{i,j}(t)

e per ogni broker bb:

Qa,b(t)=∑i,j: ai=a, bi,j=bqi,j(t)Q_{a,b}(t) = \sum_{i,j:\,a_i=a,\ b_{i,j}=b} q_{i,j}(t)

Questa seconda identità costituisce l’invariante di riconciliazione con il Portfolio Engine.

3. Classificazione degli eventi

Prima dell’applicazione delle regole FIFO, le transazioni vengono classificate in eventi di dominio.

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER
SPLIT, se l’ADJUSTMENT è collegato a un evento SPLIT


La coppia di TRANSFER è già identificata dalle due transazioni collegate tramite related_transaction_id; non necessita di un Asset Event.

Gli Asset Event restano informazioni esplicitamente collegate dall’utente e non vengono inferiti automaticamente.

4. Funzione di transizione dello stato

Sia:

Sa(t)S_a(t)

l’insieme dei lotti e frammenti dell’asset aa dopo gli eventi fino alla data tt.

Il nuovo stato è ottenuto applicando cronologicamente:

Sa(tk)=Φ(Sa(tk−1),ek)S_a(t_k) = \Phi(S_a(t_{k-1}), e_k)

dove eke_k è l’evento classificato.

A parità di data, l’ordinamento deve essere deterministico tramite identificatore transazione o altra chiave stabile.

4.1 BUY

Una BUY crea un nuovo lotto e un frammento sul broker della transazione:

Li:qi0=q,pi0=∣A∣qL_i: \quad q_i^0=q,\qquad p_i^0=\frac{|A|}{q}
BUY
└─ nuovo lotto
   └─ nuovo frammento sul broker della BUY

4.2 SELL

Una SELL di quantità qsq_s consuma FIFO i frammenti presenti sul broker della vendita.

Se:

qs=∑kqkconsumedq_s = \sum_k q_k^{consumed}

allora il ricavo unitario è:

ps=Asqsp_s = \frac{A_s}{q_s}

e il P&L FIFO attribuito al lotto LkL_k è:

P&Lksell=qkconsumed(ps−pk0)P\&L_k^{sell} = q_k^{consumed}(p_s-p_k^0)

La SELL:

riduce o chiude i frammenti;
genera incasso;
genera P&L FIFO;
non modifica il prezzo originario delle quantità residue.
4.3 ADJUSTMENT positivo

Un ADJUSTMENT positivo crea un nuovo lotto:

qi0=q,pi0=0q_i^0=q,\qquad p_i^0=0
ADJUSTMENT+
└─ nuovo lotto a costo cash nullo


Il relativo cost_basis_override continua a essere utilizzato dalla vista WAC, ma non modifica il prezzo FIFO originario.

Il P&L assoluto del lotto riflette quindi integralmente il valore ottenuto senza esborso di liquidità registrata.

Per l’analisi percentuale viene utilizzato un prezzo di riferimento distinto:

piref=MarketPricea(ti0)p_i^{ref} = MarketPrice_a(t_i^0) Returni(t)=MarketPricea(t)piref−1Return_i(t) = \frac{MarketPrice_a(t)}{p_i^{ref}}-1

Il rendimento relativo parte da 0%0\% alla data di ingresso, senza alterare il costo FIFO economico nullo.

4.4 ADJUSTMENT negativo

Un ADJUSTMENT negativo consuma FIFO i frammenti presenti sul broker.

Il ricavo è nullo:

padj=0p_{adj}=0

Pertanto:

P&Liadj=−qiconsumedpi0P\&L_i^{adj} = -q_i^{consumed}p_i^0

L’evento rappresenta una perdita o rimozione dell’asset senza incasso registrato.

Non genera cash.

4.5 TRANSFER

Una coppia TRANSFER è composta da:

gamba negativa → broker sorgente
gamba positiva → broker destinatario


La direzione dipende dal segno delle quantità, non dall’ordine cronologico delle date.

Siano doutd_{out} e dind_{in} le date delle due gambe:

tstarttransit=min⁡(dout,din)t^{transit}_{start} = \min(d_{out},d_{in}) tendtransit=max⁡(dout,din)t^{transit}_{end} = \max(d_{out},d_{in})

Al momento iniziale il transfer seleziona FIFO la quantità sul broker sorgente.

Durante l’intervallo:

[tstarttransit,tendtransit)[t^{transit}_{start},t^{transit}_{end})

i frammenti hanno custodia:

IN_TRANSIT


Alla data finale vengono assegnati al broker destinatario.

Il transfer:

preserva lotto, data e prezzo originari;
può biforcare un lotto;
non genera cash;
non genera P&L FIFO;
non fonde lotti differenti;
non utilizza il cost_basis_override nella vista FIFO.

Il cost_basis_override resta utilizzato dal Portfolio Engine per il WAC riconosciuto del broker destinatario.

4.6 SPLIT

Se un ADJUSTMENT è collegato esplicitamente a un evento SPLIT, ogni lotto aperto coinvolto viene trasformato.

Per rapporto r>0r>0:

qi′=rqiq_i' = r q_i pi0′=pi0rp_i^{0\prime} = \frac{p_i^0}{r}

Quindi:

qi′pi0′=qipi0q_i'p_i^{0\prime} = q_ip_i^0

Il costo FIFO totale resta invariato.

Lo split non crea P&L e non crea un nuovo lotto economico.

5. Stati derivati del lotto

Lo stato complessivo di un lotto è derivato dai suoi frammenti.

OPEN
    tutta o parte della quantità è ancora detenuta

PARTIALLY_CLOSED
    una parte è stata venduta o rimossa, una parte resta aperta

CLOSED
    nessuna quantità rimane aperta

IN_TRANSIT
    tutta la quantità aperta è temporaneamente in transito

DISTRIBUTED
    i frammenti aperti sono detenuti da almeno due broker


Gli stati possono essere combinati semanticamente. Per esempio un lotto può essere:

PARTIALLY_CLOSED + DISTRIBUTED


La UI può mostrare una label principale e dettagli secondari.

6. P&L e valore del lotto
6.1 Valore residuo
OpenValuei(t)=qiopen(t)⋅MarketPricea(t)OpenValue_i(t) = q_i^{open}(t)\cdot MarketPrice_a(t)
6.2 Incassi cumulati
Proceedsi(t)=∑SELL attribuiteal lotto ifino a tSellProceedsProceeds_i(t) = \sum_{\substack{\text{SELL attribuite}\\\text{al lotto }i\\\text{fino a }t}} SellProceeds

Gli ADJUSTMENT negativi non aumentano gli incassi.

6.3 Valore complessivo prodotto
TotalValuei(t)=OpenValuei(t)+Proceedsi(t)TotalValue_i(t) = OpenValue_i(t)+Proceeds_i(t)
6.4 Costo FIFO originario
OriginalCosti=qi0pi0OriginalCost_i = q_i^0p_i^0
6.5 P&L FIFO assoluto
P&Li(t)=TotalValuei(t)−OriginalCostiP\&L_i(t) = TotalValue_i(t)-OriginalCost_i
6.6 P&L di una selezione di lotti

Dato un insieme selezionato L\mathcal{L}:

OpenValueL(t)=∑i∈LOpenValuei(t)OpenValue_{\mathcal{L}}(t) = \sum_{i\in\mathcal{L}}OpenValue_i(t) ProceedsL(t)=∑i∈LProceedsi(t)Proceeds_{\mathcal{L}}(t) = \sum_{i\in\mathcal{L}}Proceeds_i(t) P&LL(t)=∑i∈LP&Li(t)P\&L_{\mathcal{L}}(t) = \sum_{i\in\mathcal{L}}P\&L_i(t)

Il confronto supporta un numero arbitrario di lotti selezionati.

7. Separazione dal WAC

La lottizzazione FIFO e il WAC sono analisi indipendenti.

FIFO
puntuale
basato sulle transazioni originarie
preserva data e prezzo
attribuisce SELL e ADJUSTMENT ai lotti
trasferisce quantità senza alterarne l’origine

WAC
scalare
aggregato per asset e broker
usa cost_basis_override
alimenta Book Value e costo riconosciuto


Nel dominio WAC:

WACa,b(t)=RecognizedCosta,b(t)Qa,b(t)WAC_{a,b}(t) = \frac{RecognizedCost_{a,b}(t)} {Q_{a,b}(t)}

Il sistema continua a produrre:

WAC per singolo broker;
WAC cumulato quando almeno due broker detengono l’asset.

Il nuovo motore FIFO non sostituisce né altera questa logica.

8. Architettura logica
                       TRANSACTION LOG
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
       Portfolio Engine              FifoLotEngine
       pool WAC aggregati            lotti e frammenti
       NAV / Book Value              SELL FIFO
       Performance                   custodia e transito
       K/R/W                         P&L per lotto
                │                           │
                └─────────────┬─────────────┘
                              ▼
                   Lots Analysis Service
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
             Prezzi           FX         WAC History
                │             │             │
                └─────────────┴─────────────┘
                              ▼
                     BULK ANALYSIS API
                              ▼
                          FRONTEND


Il FifoLotEngine è:

puro;
event-sourced;
privo di I/O;
deterministico;
calcolato dalla storia completa fino a date_to;
indipendente dal range di visualizzazione.
9. API bulk desiderata
Endpoint
POST /portfolio/lots/analysis

Richiesta concettuale
asset_id
broker_ids
date_from
date_to
target_currency
selected_lot_ids
requested_analyses


Analisi richiedibili nella stessa operazione:

LOT_SUMMARY
GANTT_TOPOLOGY
CUSTODY_HISTORY
EVENT_HISTORY
VALUE_HISTORY
RETURN_HISTORY
PRICE_HISTORY
BROKER_WAC_HISTORY
CUMULATIVE_WAC_HISTORY


Il service layer deve condividere, dentro la singola richiesta:

query delle transazioni;
caricamento degli accessi broker;
ricostruzione FIFO;
caricamento bulk dei prezzi;
caricamento bulk FX;
calcolo delle serie WAC.

Il frontend non effettua richieste separate per prezzi o FX.

Risposta concettuale
asset
target_currency
calculation_metadata

lots[]
    lot identity
    origin data
    state
    quantities
    current custody
    current value
    FIFO P&L

custody_segments[]
    lot
    broker / in-transit
    start/end
    quantity

lot_events[]
    BUY / SELL / TRANSFER / ADJUSTMENT / SPLIT
    quantity
    proceeds
    FIFO P&L

histories[]
    lot or selection
    daily open quantity
    market price
    open value
    cumulative proceeds
    total value
    absolute P&L
    relative return

wac_series[]
    broker WAC
    cumulative WAC


Tutti i valori monetari vengono restituiti nella target_currency.

10. Interfaccia utente ad alto livello
10.1 WAC e prezzo di mercato

Grafico aggregato dell’asset:

Prezzo di mercato
WAC dei singoli broker
WAC cumulato


La label Market Price deve essere inclusa nell’i18n:

IT: Prezzo di mercato
EN: Market Price
FR: Prix de marché
ES: Precio de mercado

10.2 Gantt: vita e custodia dei lotti

Ogni lane rappresenta un lotto originario.

Ogni segmento rappresenta la custodia del frammento in un intervallo temporale.

Lotto BTC  ●━━━━ Coinbase 0,15 ━┳━━ Coinbase 0,05 ━━━━━━━━━→
                                 └══ In transito ══ IBKR 0,10 ━→


Codifica visuale:

spessore     → quantità del frammento
colore       → broker
tratteggio   → in transito
opacità      → stato storico
bordo/glow   → selezione
icona asset  → label della lane
icona broker → inizio del segmento di custodia


Spessore:

Thickness(q)=Tmin+qQmax(Tmax−Tmin)Thickness(q)= T_{min} + \frac{q}{Q_{max}} (T_{max}-T_{min})

dove QmaxQ_{max} è la massima quantità originaria dei lotti dell’asset visualizzato.

Scala fissa di opacità:

ramo aperto       90%
in transito       65% + tratteggio
ramo chiuso       45%
fuori dal range   non renderizzato


La selezione non modifica l’opacità degli altri elementi.

WAC chart e Gantt condividono:

asse temporale;
zoom;
traslazione;
crosshair/axis pointer.
10.3 Tabella unica dei lotti

Non esistono più tabelle separate per aperti e chiusi.

Ogni riga rappresenta un lotto originario:

Origine
Stato
Custodia
Quantità originaria
Quantità aperta
Prezzo originario
Valore corrente
P&L FIFO


La selezione multipla esistente del DataTable determina i lotti inclusi nel grafico comparativo.

Interazioni:

click riga
→ seleziona/deseleziona lotto

click cella Custodia
→ apre modale del lotto

doppio click riga
→ scroll e pulse sul Gantt

doppio click Gantt
→ scroll e pulse sulla riga

10.4 Modale Custodia

La modale espone:

riepilogo del lotto
distribuzione corrente per broker
quantità aperta/venduta/rimossa
cronologia BUY/SELL/TRANSFER/ADJUSTMENT
intervalli in transito
branch generati dai transfer parziali


La modale sostituisce l’ipotesi di righe espandibili nel DataTable.

10.5 Grafico dei lotti selezionati

Il terzo grafico contiene tutti i lotti selezionati.

Modalità:

Valore
Rendimento
Prezzo

Valore

Mostra:

valore residuo
incassi cumulati da SELL
valore totale prodotto
P&L FIFO assoluto

Rendimento

Mostra una serie per ogni lotto selezionato e una serie aggregata opzionale.

Per BUY:

ReferencePricei=pi0ReferencePrice_i=p_i^0

Per ADJUSTMENT positivo:

ReferencePricei=MarketPricea(ti0)ReferencePrice_i=MarketPrice_a(t_i^0)

Tutte le serie partono da 0%0\% alla data di origine.

Prezzo

Mostra:

Prezzo di mercato
Prezzo di origine dei lotti selezionati
WAC cumulato
WAC dei broker coinvolti


Serie inizialmente visibili:

Prezzo di mercato
WAC cumulato
Prezzi origine


I WAC dei singoli broker restano disponibili tramite legenda.

Il grafico utilizza inizialmente lo stesso range temporale degli altri due, ma mantiene zoom indipendente, con eventuale collegamento esplicito futuro.

11. Stato desiderato del sistema
Portfolio Engine esistente
→ invariato nella responsabilità aggregata.

Nuovo FifoLotEngine
→ da creare.

calculate_fifo_lots() attuale
→ sostituito progressivamente dal nuovo motore.

get_lots() attuale
→ sostituito dalla nuova analisi bulk.

OpenLotsTable / ClosedLotsTable
→ sostituite da una tabella unificata.

BubbleLotTimeline
→ sostituita dal Gantt.

get_asset_history() attuale
→ da riesaminare, non da usare come modello per la nuova history.

AssetWacPriceChart
→ mantenuto ed evoluto per la sincronizzazione col Gantt.

DataTable
→ riutilizzato senza introdurre row expansion.

Modal
→ nuova vista dettagliata di custodia e cronologia.

12. Oggetto della successiva analisi di fattibilità

Il piano dovrà essere valutato rispetto a quattro categorie:

ESISTE
componenti e dati già disponibili e riutilizzabili;

MODIFICARE
componenti esistenti che possono evolvere senza essere sostituiti;

CREARE
nuovo engine, DTO, endpoint, Gantt, modale e history batch;

RIMUOVERE
motore FIFO e componenti UI resi obsoleti.


L’analisi dovrà inoltre identificare:

incoerenze matematiche;
problemi di identità stabile dei lotti;
gestione delle coppie TRANSFER;
ordinamento same-day;
costo computazionale;
query e caricamenti bulk;
compatibilità con share percentage;
conversione FX;
validazione degli split;
strategia di migrazione e test di riconciliazione;
eventuali funzionalità da rinviare, in particolare short selling e cache backend.

Questa costituisce la specifica di destinazione: descrive che cosa il sistema deve rappresentare, senza vincolare prematuramente il dettaglio implementativo.



Appendice A — Specifica visuale dell’interfaccia FIFO a segmenti
A.1 Obiettivo informativo

L’interfaccia proposta articola l’analisi dell’asset in quattro viste coordinate:

WAC e prezzo di mercato: rappresentazione aggregata della posizione;
vita e custodia dei lotti: rappresentazione temporale mediante Gantt;
tabella unificata dei lotti: rappresentazione sintetica e selezionabile dello stato;
confronto dei lotti selezionati: analisi storica in valore, rendimento e prezzo.

La struttura complessiva è la seguente:

┌──────────────────────────────────────────────────────────────────────────┐
│  ASSET HEADER                                                            │
│  [icona] Nome asset · valuta · quantità complessiva · valore corrente    │
├──────────────────────────────────────────────────────────────────────────┤
│  WAC / PREZZO DI MERCATO                                                 │
│  Vista aggregata dell'asset e dei broker                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  VITA E CUSTODIA DEI LOTTI                                               │
│  Gantt temporale sincronizzato con il grafico WAC                        │
├──────────────────────────────────────────────────────────────────────────┤
│  TABELLA UNIFICATA DEI LOTTI                                             │
│  Stato, custodia, quantità, valore e P&L FIFO                            │
├──────────────────────────────────────────────────────────────────────────┤
│  CONFRONTO DEI LOTTI SELEZIONATI                                         │
│  [Valore] [Rendimento] [Prezzo]                                          │
└──────────────────────────────────────────────────────────────────────────┘

A.2 Header dell’asset

L’header identifica il dominio comune delle quattro viste.

┌──────────────────────────────────────────────────────────────────────────┐
│ [asset icon]  Bitcoin                                      [↻ Aggiorna] │
│               BTC · USD                                                │
│                                                                          │
│ Quantità totale        Valore corrente       Broker coinvolti           │
│ 0,150000 BTC           9.450,00 €            Coinbase · IBKR             │
└──────────────────────────────────────────────────────────────────────────┘


Informazioni minime:

asset
ticker o simbolo
valuta nativa
quantità totale nello scope
valore corrente nella target currency
broker che detengono quantità aperte


L’icona dell’asset viene utilizzata coerentemente anche nelle lane del Gantt e nella modale di custodia.

A.3 Grafico aggregato WAC e prezzo di mercato
A.3.1 Struttura

Il primo grafico conserva la responsabilità aggregata già esistente.

┌──────────────────────────────────────────────────────────────────────────┐
│ WAC / Prezzo di mercato                         [ Assoluto ] [ % ]       │
│                                                                          │
│ 140 ┤                                                      ╭──── Mercato│
│ 120 ┤                                          ╭───────────╯             │
│ 100 ┤──────────────────── WAC cumulato ────────────────                   │
│  80 ┤         ┌──── WAC Coinbase ─────┐                                  │
│  60 ┤─────────┘                       └──── WAC IBKR ─────                │
│  40 ┤                                                                      │
│     └───────┬────────┬────────┬────────┬────────┬────────┬───────────────│
│           feb      mar      apr      mag      giu      lug               │
│                                                                          │
│ Legenda: ● Prezzo di mercato  ─ WAC cumulato  ─ Coinbase  ─ IBKR         │
└──────────────────────────────────────────────────────────────────────────┘


Serie previste:

Prezzo di mercato
WAC del singolo broker
WAC cumulato, se almeno due broker detengono l’asset


La legenda consente di attivare o disattivare le singole serie.

La label Market Price deve essere localizzata:

IT  Prezzo di mercato
EN  Market Price
FR  Prix de marché
ES  Precio de mercado

A.3.2 Marker degli eventi

Le transazioni che modificano l’asset possono apparire come marker discreti:

                    BUY       SELL       TRANSFER       ADJUSTMENT
                     ●          ◆            ⇄               ±
Prezzo ──────────────●──────────◆────────────⇄───────────────±──────


I marker non sostituiscono il Gantt. Servono come riferimenti puntuali sul grafico aggregato.

Tooltip del marker:

18 giugno 2026

Acquisto
Quantità             +0,150000 BTC
Ammontare             -200,00 €
Broker                Coinbase
Prezzo unitario       1.333,33 €/BTC

A.4 Gantt — Vita e custodia dei lotti
A.4.1 Struttura generale

Ogni lane rappresenta un lotto originario. I segmenti interni descrivono la custodia e la quantità lungo il tempo.

┌──────────────────────────────────────────────────────────────────────────┐
│ Vita e custodia dei lotti                    [ Aperti ] [ Tutti ]        │
│                                                                          │
│                              feb   mar   apr   mag   giu   lug            │
│                              │     │     │     │     │     │              │
│ [asset] Lotto 17 feb · 2     ●━━━━━━ Directa · 2 ━━━━━━━━━━━━━━━━━━━→    │
│                                                                          │
│ [asset] Lotto 4 mar · 2            ●━━━━ Directa · 2 ━━━━━━━━━━━━━━━→    │
│                                                                          │
│ [asset] Lotto 1 apr · 1                  ●━━ Directa · 1 ━━━━━━━━━━━→    │
│                                                                          │
│ [asset] Lotto BTC · 0,15                            ●━━━━ Coinbase 0,15  │
│                                                      ├━━ Coinbase 0,05 →│
│                                                      └══ Transito ══     │
│                                                                └━ IBKR →│
│                                                                          │
│                              [──────── zoom temporale ────────]           │
└──────────────────────────────────────────────────────────────────────────┘


Il grafico WAC e il Gantt condividono:

asse temporale
intervallo visibile
zoom
traslazione
crosshair


Un’operazione di zoom o pan su uno dei due aggiorna l’altro.

A.4.2 Codifica visuale
Spessore     quantità del frammento
Colore       broker custode
Tratteggio   stato IN_TRANSIT
Opacità      stato aperto o storico
Bordo/glow   selezione
Icona        asset o broker


Scala fissa di opacità:

Ramo aperto                  90%
In transito                  65% + tratteggio
Ramo chiuso                  45%
Fuori dal range              non renderizzato


La selezione non modifica l’opacità degli altri segmenti.

Il lotto selezionato viene evidenziato mediante:

bordo più spesso
glow esterno
marker iniziale accentuato
pulse temporaneo in caso di navigazione sincronizzata

A.4.3 Spessore proporzionale

Sia:

Qmax⁡=max⁡iqi0Q_{\max} = \max_i q_i^0

la massima quantità originaria tra i lotti dell’asset visualizzato.

Lo spessore di un frammento di quantità qq è:

Thickness(q)=Tmin⁡+qQmax⁡(Tmax⁡−Tmin⁡)Thickness(q) = T_{\min} + \frac{q}{Q_{\max}} (T_{\max}-T_{\min})

con:

Tmin = spessore minimo leggibile
Tmax = spessore massimo
q = 0 → segmento assente


Rappresentazione esemplificativa:

100 unità  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 60 unità  ━━━━━━━━━━━━━━━━━━━━━
 20 unità  ━━━━━━━━━
  1 unità  ━━━━━


Lo spessore rappresenta la quantità, non il valore di mercato. Pertanto cambia soltanto in seguito a:

SELL
ADJUSTMENT
TRANSFER parziale
SPLIT


e non oscilla quotidianamente con il prezzo.

A.5 Biforcazione da trasferimento parziale
A.5.1 Caso elementare
BUY Coinbase        +0,15 BTC
TRANSFER Coinbase   -0,10 BTC
TRANSFER IBKR       +0,10 BTC


Visualizzazione:

Tempo ───────────────────────────────────────────────────────────────────→

                                   inizio transito      fine transito
                                          │                  │
Lotto BTC  ●━━━━━━━━ Coinbase 0,15 ━━━━━━━━┿━━━━━━━━━━━━━━━━━━┿━━━━━━━━━
                                          │                  │
                                          ├━━ Coinbase 0,05 ━━━━━━━━━━━→
                                          │
                                          └══ Transito 0,10 ═╸
                                                             └━━ IBKR
                                                                 0,10 ━→


La biforcazione non crea un nuovo lotto originario. Genera due frammenti appartenenti al medesimo lotto.

A.5.2 Transfer di ritorno
Coinbase → IBKR       0,10 BTC
IBKR → Coinbase       0,05 BTC

Tempo ───────────────────────────────────────────────────────────────────→

                     ┌━━ Coinbase 0,05 ━━━━━━━━━━━━━━━┳━━ Coinbase 0,10 ━→
Lotto BTC ●━━━━━━━━━━┤                                │
                     └══ Transito ══ IBKR 0,10 ━━━━━━━┻━━ IBKR 0,05 ━━━→


La rappresentazione comunica contemporaneamente:

origine comune;
biforcazione;
quantità di ogni ramo;
variazione della custodia;
permanenza del lotto nel tempo.
A.5.3 Date delle gambe fuori ordine

La rappresentazione usa:

tstart=min⁡(dout,din)t_{start}=\min(d_{out},d_{in}) tend=max⁡(dout,din)t_{end}=\max(d_{out},d_{in})

La direzione è determinata dai segni delle quantità.

data minore                                      data maggiore
    │                                                 │
    └════════════ quantità in transito ═══════════════┘


Le date originali delle due gambe restano consultabili nel tooltip e nella modale.

A.6 Vendita e riduzione di un lotto
A.6.1 Vendita parziale
BUY 10
SELL 4

Lotto A  ●━━━━━━━━━━━━━━━━━━━━◆━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
         10                   SELL 4
                              residuo 6

Spessore:
prima della SELL   ━━━━━━━━━━━━━━━━━━━━━━━
dopo la SELL       ━━━━━━━━━━━━━━━


Tooltip sulla vendita:

Vendita parziale

Data                 20 giugno 2026
Broker               Directa
Quantità venduta     4
Quantità residua     6
Ricavo attribuito    480,00 €
P&L FIFO             +80,00 €

A.6.2 Vendita completa
Lotto A  ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◆
         BUY                                       SELL completa


Il segmento termina nel punto della SELL.

Un lotto completamente chiuso:

non prosegue oltre la data di chiusura;
è mostrato al 45% di opacità nella modalità Tutti;
è assente nella modalità Aperti.
A.6.3 Vendita completa di un singolo ramo
                        ┌━━ Coinbase 0,10 ━━━━━━━━━◆ chiuso
Lotto BTC ●━━━━━━━━━━━━━┤
                        └━━ IBKR 0,05 ━━━━━━━━━━━━━━━━━━━━━→


Stato complessivo:

Parzialmente chiuso


Custodia corrente:

IBKR


Quantità aperta:

0,05 BTC

A.7 Adjustment
A.7.1 Adjustment positivo
ADJUSTMENT +5


Crea un lotto a costo FIFO cash nullo:

[asset] Lotto adjustment · 5   ±━━━━━━━━ Broker · 5 ━━━━━━━━━━━━━→


Tooltip:

Rettifica positiva

Data                  12 maggio 2026
Broker                Directa
Quantità ricevuta     5
Costo cash FIFO       0,00 €
Prezzo di riferimento 80,00 €


Il prezzo di riferimento è il prezzo di mercato alla data di acquisizione ed è utilizzato esclusivamente per il rendimento percentuale.

A.7.2 Adjustment negativo
ADJUSTMENT -3


Consuma FIFO con ricavo nullo:

Lotto A  ●━━━━━━━━━━━━━━━━━━×━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
         10                 Adjustment -3
                            residuo 7


Tooltip:

Rettifica negativa

Quantità rimossa      3
Incasso               0,00 €
Costo FIFO rimosso    300,00 €
P&L FIFO              -300,00 €

A.7.3 Split

Uno split non crea una nuova lane. Determina una trasformazione dello spessore e del prezzo unitario:

                         SPLIT 2:1
                             │
Lotto A  ●━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
         10 @100             │ 20 @50

Spessore prima   ━━━━━━━━━━━━━
Spessore dopo    ━━━━━━━━━━━━━━━━━━━━━━━


Tooltip:

Split 2:1

Quantità precedente       10
Quantità successiva       20
Prezzo FIFO precedente    100,00 €
Prezzo FIFO successivo     50,00 €
Costo totale             1.000,00 € → 1.000,00 €

A.8 Tabella unificata dei lotti
A.8.1 Struttura
┌──────────────────────────────────────────────────────────────────────────┐
│ Lotti                                            Stato: Tutti ▾          │
│                                                  Broker: Tutti ▾         │
│                                                  [Cerca...]              │
├───┬────────────┬─────────────────┬───────────────┬─────────┬─────────────┤
│   │ Origine    │ Stato           │ Custodia      │ Q.tà    │ Prezzo orig.│
├───┼────────────┼─────────────────┼───────────────┼─────────┼─────────────┤
│ ☑ │ 17/02/2025 │ Aperto          │ Directa       │ 2       │ 54,98 €     │
│ ☑ │ 04/03/2025 │ Parziale        │ Directa       │ 1 / 2   │ 46,85 €     │
│ ☐ │ 01/04/2025 │ Chiuso          │ —             │ —       │ 43,52 €     │
│ ☑ │ 18/06/2026 │ Distribuito     │ 2 broker  [>] │ 0,15 BTC│ 1.333,33 € │
└───┴────────────┴─────────────────┴───────────────┴─────────┴─────────────┘


Colonne complete proposte:

selezione
origine
tipo origine
stato
custodia
quantità originaria
quantità aperta
prezzo originario
valore corrente
P&L FIFO


Una sola riga rappresenta il lotto originario anche quando il lotto possiede più branch.

A.8.2 Stati visuali
Aperto
Parzialmente chiuso
Chiuso
In transito
Distribuito
Rimosso


Esempi:

Aperto
2 quote ancora detenute integralmente

Parzialmente chiuso
1 quota aperta su 2 originarie

Distribuito
quantità aperta contemporaneamente su almeno due broker

In transito
tutta la quantità aperta è temporaneamente in transito

Chiuso
nessuna quantità aperta


Lo stato può essere rappresentato con un badge, mentre i dettagli restano nella modale.

A.9 Sincronizzazione Gantt e tabella
A.9.1 Selezione

Il click sulla riga utilizza la selezione multipla già disponibile nel DataTable.

Click riga
      │
      ├─ aggiorna selectedLotIds
      ├─ evidenzia il lotto nel Gantt
      └─ aggiorna il grafico comparativo


La selezione nel Gantt aggiorna simmetricamente il DataTable.

A.9.2 Doppio click e pulse
Doppio click sulla riga
      │
      ├─ scroll al lotto nel Gantt
      └─ pulse temporaneo del segmento

Doppio click sul Gantt
      │
      ├─ scroll alla riga del DataTable
      └─ pulse temporaneo della riga


Effetto pulse:

stato normale     ━━━━━━━━━━━━━━━━━
pulse 1           ╔━━━━━━━━━━━━━━━━╗
pulse 2            ━━━━━━━━━━━━━━━━━


Il pulse non altera persistentemente colore, spessore od opacità.

A.10 Modale di custodia
A.10.1 Apertura

La modale si apre mediante click sulla cella Custodia:

│ Distribuito │ 2 broker [>] │
                           click


La selezione della riga e l’apertura della modale sono azioni distinte.

A.10.2 Struttura proposta
┌──────────────────────────────────────────────────────────────────────┐
│ [asset icon] Lotto Bitcoin — 18 giugno 2026                     [X] │
│ Acquisto originario su Coinbase                                     │
├──────────────────────────────────────────────────────────────────────┤
│ RIEPILOGO                                                            │
│                                                                      │
│ Quantità originaria       0,150000 BTC                              │
│ Quantità aperta           0,150000 BTC                              │
│ Quantità venduta          —                                         │
│ Quantità rimossa          —                                         │
│ Prezzo FIFO originario    1.333,33 €/BTC                            │
│ Costo cash originario       200,00 €                                │
│ Stato                     Distribuito                               │
├──────────────────────────────────────────────────────────────────────┤
│ CUSTODIA ATTUALE                                                     │
│                                                                      │
│ [Coinbase icon] Coinbase                                             │
│ Quantità                  0,100000 BTC                              │
│ Stato                     Aperto                                    │
│ Dal                       10 luglio 2026                             │
│                                                                      │
│ [IBKR icon] Interactive Brokers                                      │
│ Quantità                  0,050000 BTC                              │
│ Stato                     Aperto                                    │
│ Dal                       6 luglio 2026                              │
├──────────────────────────────────────────────────────────────────────┤
│ CRONOLOGIA                                                           │
│                                                                      │
│ 18/06  ● BUY Coinbase                  +0,150000 BTC                 │
│ 06/07  ⇄ Transfer Coinbase → IBKR       0,100000 BTC                 │
│          └─ In transito: 06/07–08/07                                │
│ 10/07  ⇄ Transfer IBKR → Coinbase       0,050000 BTC                 │
│          └─ Regolato nello stesso giorno                            │
├──────────────────────────────────────────────────────────────────────┤
│                                          [Chiudi] [Vai alla transazione]│
└──────────────────────────────────────────────────────────────────────┘

A.10.3 Caso con vendite
┌──────────────────────────────────────────────────────────────┐
│ CUSTODIA E CHIUSURE                                          │
│                                                              │
│ Coinbase                                                     │
│ Quantità originaria sul ramo      0,100000 BTC              │
│ Quantità venduta                  0,100000 BTC              │
│ Stato                            Chiuso                     │
│ Data chiusura                    20 luglio 2026             │
│ P&L FIFO                         +120,00 €                  │
│                                                              │
│ IBKR                                                         │
│ Quantità aperta                   0,050000 BTC              │
│ Stato                            Aperto                     │
└──────────────────────────────────────────────────────────────┘

A.11 Grafico dei lotti selezionati

La selezione multipla della tabella alimenta il terzo grafico.

┌──────────────────────────────────────────────────────────────────────────┐
│ 3 lotti selezionati                   [ Valore ] [ Rendimento ] [ Prezzo ]│
│                                                                          │
│ ☑ Lotto 17/02 @54,98                                                     │
│ ☑ Lotto 04/03 @46,85                                                     │
│ ☑ Lotto BTC 18/06                                                       │
└──────────────────────────────────────────────────────────────────────────┘


Non viene imposto un limite al numero di lotti selezionabili.

A.12 Modalità Valore
A.12.1 Singolo lotto
┌──────────────────────────────────────────────────────────────────────────┐
│ Valore del lotto                                                         │
│                                                                          │
│ 350 € ┤                                    █████ Incassi da vendite      │
│ 300 € ┤                              ███████████                          │
│ 250 € ┤                    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ Valore residuo             │
│ 200 € ┼──────────────────── Costo cash originario ─────────────────────  │
│ 150 € ┤         ▓▓▓▓▓▓▓▓▓▓                                                 │
│ 100 € ┤   ▓▓▓▓▓▓                                                           │
│   0 € ┼──●──────────────◆─────────────────────────────────────────────── │
│       BUY             SELL parziale                                  oggi│
│                                                                          │
│ Totale prodotto = Valore residuo + Incassi da vendite                   │
└──────────────────────────────────────────────────────────────────────────┘


Codifica:

area inferiore   valore di mercato della quantità aperta
area superiore   incassi cumulati attribuiti al lotto
linea soglia     costo cash originario

A.12.2 Selezione multipla
┌──────────────────────────────────────────────────────────────────────────┐
│ Valore dei lotti selezionati                                             │
│                                                                          │
│ 900 € ┤                              █████████ Incassi complessivi       │
│ 750 € ┤                    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ Valore residuo             │
│ 600 € ┼──────────── Costo originario complessivo ─────────────────────  │
│ 450 € ┤          ▓▓▓▓▓▓▓▓▓▓                                               │
│ 300 € ┤   ▓▓▓▓▓▓                                                            │
│   0 € ┼────────────────────────────────────────────────────────────────  │
│                                                                          │
│ Legenda: Totale selezione · Lotto 17/02 · Lotto 04/03 · Lotto BTC       │
└──────────────────────────────────────────────────────────────────────────┘


La visualizzazione principale è aggregata. Il tooltip restituisce il breakdown per lotto.

A.13 Modalità Rendimento
A.13.1 BUY

Ogni linea parte da 0%0\% alla propria data d’origine.

┌──────────────────────────────────────────────────────────────────────────┐
│ Rendimento FIFO                                                          │
│                                                                          │
│ 180% ┤                         ╭──────── Lotto 04/03                      │
│ 150% ┤              ╭──────────╯                                         │
│ 120% ┤       ╭──────╯          ╭──────── Lotto 17/02                     │
│  90% ┤   ╭───╯       ╭─────────╯                                         │
│  60% ┤   │      ╭────╯                                                    │
│  30% ┤   │  ╭───╯                                                         │
│   0% ┼───●──●────────────────────────────────────────────────────────── │
│      17/02 04/03                                                    oggi │
└──────────────────────────────────────────────────────────────────────────┘

A.13.2 ADJUSTMENT positivo

Il lotto ha costo cash FIFO nullo, ma la serie relativa utilizza il prezzo di mercato alla data di ingresso:

Costo cash FIFO        0,00 €
Prezzo di riferimento  80,00 €

Rendimento dalla ricezione

 50% ┤                                      ╭────────
 25% ┤                            ╭─────────╯
  0% ●────────────────────────────╯
     data adjustment                         oggi


Il tooltip distingue esplicitamente:

P&L FIFO assoluto
Rendimento dalla data di ricezione

A.14 Modalità Prezzo
┌──────────────────────────────────────────────────────────────────────────┐
│ Prezzo e costo medio                                                     │
│                                                                          │
│ 160 ┤                                        ╭──── Prezzo di mercato    │
│ 140 ┤                              ╭─────────╯                           │
│ 120 ┼──────── Prezzo origine Lotto A ─────────────────────────────────  │
│ 100 ┼──────── Prezzo origine Lotto B ─────────────────────────────────  │
│  90 ┤             ┌──── WAC cumulato ─────────────────────────────      │
│  80 ┤─────────────┘                                                       │
│  70 ┤       ┌──── WAC Coinbase ─────                                     │
│  60 ┤       └──────────── WAC IBKR ─────────────────────────────         │
│     └─────────────────────────────────────────────────────────────────  │
│                                                                          │
│ Legenda scrollabile                                                      │
└──────────────────────────────────────────────────────────────────────────┘


Visibili inizialmente:

Prezzo di mercato
Prezzi originari dei lotti selezionati
WAC cumulato


Disponibili in legenda:

WAC dei singoli broker coinvolti


Se un solo broker detiene l’asset:

WAC broker visibile
WAC cumulato omesso perché ridondante

A.15 Sincronizzazione temporale
A.15.1 WAC e Gantt

I primi due grafici condividono sempre lo stesso intervallo:

┌────────────────────────────────────────────────────────────┐
│ WAC / Prezzo       │<────── intervallo visibile ──────>| │
├────────────────────────────────────────────────────────────┤
│ Gantt              │<────── intervallo visibile ──────>| │
└────────────────────────────────────────────────────────────┘
                       [──── slider comune ────]


Azioni sincronizzate:

zoom
pan
slider
crosshair
selezione intervallo

A.15.2 Grafico dei lotti selezionati

Il terzo grafico riceve inizialmente lo stesso range, ma mantiene zoom indipendente.

WAC + Gantt       [ 1 gennaio ───────────── 15 luglio ]
Grafico confronto [ 1 gennaio ───────────── 15 luglio ]

Dopo zoom locale:

WAC + Gantt       [ 1 gennaio ───────────── 15 luglio ]
Grafico confronto              [ 1 giugno ─ 15 luglio ]


Un collegamento opzionale futuro può consentire:

[🔗 Sincronizza intervallo]


Il crosshair può restare condiviso anche quando gli zoom sono indipendenti.

A.16 Comportamento rispetto al range
Lotto nato prima del range
Range visibile
│
│ ←━━━━ Directa · 2 quote ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
│


La freccia sinistra indica che il segmento esisteva già prima del range.

Lotto aperto oltre date_to
━━━━━━━━━━━━━━━━ Directa · 2 quote ━━━━━→ │
                                           fine range

Lotto chiuso interamente prima del range
non renderizzato

Lotto nato e chiuso nel range
          ●━━━━━━━━━━━━◆
          BUY          SELL


Il calcolo viene effettuato dall’inizio della storia; il range limita esclusivamente il materiale visualizzato.

A.17 Stato vuoto e caricamento
Nessun lotto
┌──────────────────────────────────────────────────────────────────┐
│ Vita e custodia dei lotti                                       │
│                                                                  │
│                  Nessun lotto disponibile                        │
│      Registra un acquisto o una rettifica positiva per iniziare.│
└──────────────────────────────────────────────────────────────────┘

Nessuna selezione
┌──────────────────────────────────────────────────────────────────┐
│ Confronto lotti                                                   │
│                                                                  │
│             Seleziona uno o più lotti nella tabella              │
│          per visualizzarne valore, rendimento e prezzo.          │
└──────────────────────────────────────────────────────────────────┘

Loading

Il contenuto precedente resta visibile con stato attenuato:

┌──────────────────────────────────────────────────────────────────┐
│ [contenuto precedente al 55%]                      ⟳ Aggiornamento│
└──────────────────────────────────────────────────────────────────┘


La selezione viene mantenuta quando gli stessi lot_id sono ancora presenti nella nuova risposta.

A.18 Vista mobile

Su schermi ridotti l’ordine rimane verticale:

┌──────────────────────────────┐
│ Asset header                 │
├──────────────────────────────┤
│ WAC / Prezzo                 │
│ [grafico scrollabile]        │
├──────────────────────────────┤
│ Gantt                        │
│ [scroll orizzontale]         │
├──────────────────────────────┤
│ Tabella / lista lotti        │
│ [checkbox] Lotto 17/02       │
│ [checkbox] Lotto 04/03       │
│ [checkbox] Lotto BTC         │
├──────────────────────────────┤
│ Confronto selezione          │
│ [Valore][Rend.][Prezzo]      │
└──────────────────────────────┘


La cella Custodia può diventare un pulsante esplicito:

[ 2 broker · Dettagli ]


La modale diventa un drawer o una modale full-screen:

┌──────────────────────────────┐
│ Lotto BTC               [X]  │
├──────────────────────────────┤
│ Riepilogo                    │
├──────────────────────────────┤
│ Custodia corrente            │
├──────────────────────────────┤
│ Cronologia                   │
└──────────────────────────────┘

A.19 Diagramma finale delle interazioni
                       ┌───────────────────────┐
                       │ WAC / Prezzo mercato  │
                       └──────────┬────────────┘
                                  │ zoom/pan condiviso
                                  ▼
┌─────────────┐         ┌───────────────────────┐
│ DataTable   │◄───────►│ Gantt vita/custodia  │
│ selezione   │  sync   │ click/doppio click   │
└──────┬──────┘         └──────────┬────────────┘
       │                            │
       │ selectedLotIds             │ click segmento
       ▼                            ▼
┌───────────────────────┐   ┌───────────────────────┐
│ Confronto selezionati │   │ Modale custodia       │
│ Valore/Rend./Prezzo   │   │ branch + cronologia   │
└───────────────────────┘   └───────────────────────┘

A.20 Sintesi delle responsabilità visuali
WAC / Prezzo di mercato
→ costo medio e mercato a livello aggregato.

Gantt
→ nascita, durata, riduzione, biforcazione, custodia e transito.

Tabella
→ stato sintetico, ricerca, filtro e selezione multipla.

Modale
→ dettagli dei branch e cronologia completa di un lotto.

Grafico di confronto
→ risultato economico e andamento dei lotti scelti.


Questa appendice completa la specifica matematica definendo la struttura visuale di destinazione, senza imporre la tecnica implementativa dei singoli componenti.


