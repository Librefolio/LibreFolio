LibreFolio FIFO Lot Engine
Modello matematico, algoritmo event-driven, architettura e interfaccia visuale

Stato: piano ad alto livello
 Ambito: analisi puntuale dei lotti, custodia, trasferimenti, rettifiche, split e posizioni short
 Principio architetturale: separazione tra analisi FIFO puntuale e calcolo WAC aggregato

1. Obiettivo

Si propone l’introduzione di un nuovo FifoLotEngine, puro ed event-sourced, finalizzato a ricostruire la storia economica e custodiale dei lotti di un asset.

Il motore deve determinare:

quali transazioni originano un lotto;
quali eventi ne riducono o chiudono la quantità;
come un lotto si distribuisce tra broker differenti;
quali quantità si trovano temporaneamente in transito;
quali transazioni generano incassi e P&L FIFO;
come split e reverse split trasformano i lotti nel tempo;
come rappresentare simmetricamente posizioni LONG e SHORT;
quali informazioni fornire a tabella, Gantt, modale e grafici comparativi.

Il nuovo motore non sostituisce il Portfolio Engine esistente.

Portfolio Engine
→ stato patrimoniale aggregato
→ NAV, Book Value, WAC, performance, K/R/W

FifoLotEngine
→ storia puntuale dei lotti
→ FIFO, custodia, transfer, P&L per lotto

2. Assunti fondamentali
2.1 Ledger come fonte primaria

Le transazioni salvate costituiscono la fonte di verità.

Il motore non tenta di correggere automaticamente dati incompleti o semanticamente errati, ma deve:

applicare regole deterministiche;
evidenziare le incoerenze;
evitare risultati silenziosamente falsi;
restituire output parziali quando possibile.
2.2 Quantità assolute

Il FifoLotEngine opera sulle quantità assolute registrate nei broker.

La proprietà share_percentage non appartiene al dominio FIFO e non viene applicata ai lotti.

QFIFO=QledgerQ^{FIFO}=Q^{ledger}

La proiezione patrimoniale per utente resta responsabilità del Portfolio Engine.

2.3 Separazione FIFO/WAC

Il FIFO è una rappresentazione puntuale:

quale quantità deriva da quale apertura;
quando è stata aperta;
a quale prezzo;
come è stata chiusa o trasferita.


Il WAC è una rappresentazione scalare:

qual è il costo medio riconosciuto
dell’intera posizione di un asset su un broker.


Il cost_basis_override continua a essere utilizzato dal dominio WAC, ma non sostituisce il prezzo originario dei lotti FIFO trasferiti.

2.4 Nessuna fusione implicita

Ogni transazione che apre una posizione genera un lotto distinto.

Due BUY nella stessa data e allo stesso prezzo non vengono fuse.

Questa scelta preserva:

auditabilità;
relazione con la transazione originaria;
identità stabile;
ordinamento FIFO deterministico.
2.5 Eventi asset

Gli Asset Event non modificano automaticamente il portafoglio.

L’utente collega esplicitamente una transazione a un evento.

Tra gli eventi attualmente previsti, soltanto lo SPLIT modifica la matematica dei lotti.

DIVIDEND             → descrittivo per FIFO
INTEREST             → descrittivo per FIFO
PRICE_ADJUSTMENT     → descrittivo per FIFO
MATURITY_SETTLEMENT  → descrittivo; gli effetti dipendono dalle transazioni
SPLIT                → algoritmico

3. Definizioni
3.1 Direzione della posizione

Ogni lotto ha una direzione immutabile:

di∈{LONG,SHORT}d_i\in\{LONG,SHORT\}

La quantità del lotto è sempre positiva.

LONG
→ asset posseduto

SHORT
→ obbligazione aperta mediante vendita allo scoperto


Non vengono utilizzati “lotti negativi”.

3.2 Lotto

Un lotto LiL_i è definito da:

Li=(idi, ai, di, ti0, qi0, pi0, ci, oi)L_i= \left( id_i,\, a_i,\, d_i,\, t_i^0,\, q_i^0,\, p_i^0,\, c_i,\, o_i \right)

dove:

idiid_i: identificatore stabile;
aia_i: asset;
did_i: direzione LONG o SHORT;
ti0t_i^0: data di apertura;
qi0>0q_i^0>0: quantità originaria;
pi0≥0p_i^0\ge0: prezzo unitario di apertura;
cic_i: valuta originaria;
oio_i: transazione di apertura.

L’identificatore naturale del lotto deriva dalla transazione di apertura:

lot_id = opening_transaction_id

3.3 Frammento di custodia

Un lotto può essere suddiviso in più frammenti:

Fi,j=(idi,j, Li, bi,j, qi,j, [ti,jstart,ti,jend), si,j)F_{i,j}= \left( id_{i,j},\, L_i,\, b_{i,j},\, q_{i,j},\, [t_{i,j}^{start},t_{i,j}^{end}),\, s_{i,j} \right)

dove:

idi,jid_{i,j}: identità stabile del frammento;
LiL_i: lotto originario;
bi,jb_{i,j}: broker custode oppure IN_TRANSIT;
qi,j>0q_{i,j}>0: quantità;
[tstart,tend)[t^{start},t^{end}): intervallo di validità;
si,js_{i,j}: stato.

L’identità del frammento deriva dall’evento che ne apre il ramo:

lot:{lot_id}/origin:{broker_id}

lot:{lot_id}/transfer:{transfer_pair_id}/to:{broker_id}


Una vendita parziale può chiudere un intervallo e aprirne uno successivo con quantità ridotta senza modificare l’identità logica del branch.

3.4 Quantità aperta

La quantità aperta di un lotto è:

qiopen(t)=∑jqi,j(t)q_i^{open}(t)=\sum_j q_{i,j}(t)

La quantità assoluta dell’asset sul broker bb è:

Qa,b(t)=∑i,jai=abi,j=bσ(di) qi,j(t)Q_{a,b}(t)= \sum_{\substack{i,j\\a_i=a\\b_{i,j}=b}} \sigma(d_i)\,q_{i,j}(t)

dove:

σ(LONG)=+1\sigma(LONG)=+1 σ(SHORT)=−1\sigma(SHORT)=-1

Questa identità deve riconciliarsi con il saldo assoluto del ledger.

4. Classificazione degli eventi

Le transazioni che modificano la quantità di un asset vengono convertite in eventi di dominio:

OPEN_LONG
CLOSE_LONG
OPEN_SHORT
CLOSE_SHORT
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER
SPLIT


Le transazioni sorgente rilevanti sono:

BUY
SELL
ADJUSTMENT
TRANSFER


La funzione di transizione dello stato è:

Sa(tk)=Φ(Sa(tk−1),ek)S_a(t_k)=\Phi\left(S_a(t_{k-1}),e_k\right)

Gli eventi sono ordinati per:

(date, transaction_id)(date,\ transaction\_id)

salvo gli eventi SPLIT, applicati all’inizio della rispettiva data.

5. Apertura e chiusura LONG/SHORT
5.1 BUY

Una BUY svolge due operazioni in sequenza:

chiude FIFO eventuali lotti SHORT aperti;
l’eventuale quantità residua apre un nuovo lotto LONG.

Il prezzo unitario è:

pbuy=∣A∣qp_{buy}=\frac{|A|}{q}

dove AA è l’ammontare totale e qq la quantità.

Chiusura SHORT

Per quantità qcq_c:

P&Lshort=qc(popenshort−pbuy)P\&L_{short} = q_c(p_{open}^{short}-p_{buy})
Apertura LONG

Se resta quantità qr>0q_r>0:

Lnew=(LONG,qr,pbuy)L_{new}=(LONG,q_r,p_{buy})
5.2 SELL

Una SELL:

chiude FIFO i lotti LONG aperti;
se resta quantità e il broker consente lo short, apre un lotto SHORT.

Il prezzo unitario è:

psell=Aqp_{sell}=\frac{A}{q}
Chiusura LONG
P&Llong=qc(psell−popenlong)P\&L_{long} = q_c(p_{sell}-p_{open}^{long})
Apertura SHORT

Se resta quantità qr>0q_r>0:

Lnew=(SHORT,qr,psell)L_{new}=(SHORT,q_r,p_{sell})

Se il broker non consente shorting, qualsiasi eccedenza costituisce un errore di consistenza.

5.3 Attraversamento dello zero

Esempio:

LONG disponibili   5 @100
SELL                8 @120


Risultato:

LONG chiuso
5 @100 vendute @120
P&L = +100

SHORT aperto
3 @120


ASCII:

LONG  5 @100  ━━━━━━━━━━━━━━━━━━━◆ chiusura
                                      │
ZERO  ────────────────────────────────┼────────────────────
                                      │
SHORT                                 ●━━━━━━━━ 3 @120 ━━━→


L’operazione inversa avviene per una BUY che chiude uno SHORT e apre un LONG con l’eccedenza.

6. Adjustment
6.1 Adjustment positivo

Un ADJUSTMENT+ rappresenta una quantità acquisita senza uscita di liquidità registrata.

Svolge:

chiusura FIFO di eventuali SHORT;
apertura di un LONG per l’eccedenza.

Il prezzo FIFO economico dell’eccedenza è:

p0=0p^0=0

Il cost_basis_override non modifica il prezzo FIFO, ma continua ad alimentare il dominio WAC.

6.2 Rendimento relativo di un Adjustment positivo

Poiché il costo economico è nullo, il rendimento percentuale tradizionale non è definito.

Si introduce un prezzo di riferimento:

piref=MarketPricea(ti0)p_i^{ref}=MarketPrice_a(t_i^0)

con politica:

1. prezzo esatto alla data;
2. altrimenti ultimo prezzo precedente;
3. altrimenti rendimento relativo non disponibile.


Il rendimento relativo è:

Returni(t)=MarketPricea(t)piref−1Return_i(t)= \frac{MarketPrice_a(t)}{p_i^{ref}}-1

La serie parte da 0%0\% alla data di ingresso.

6.3 Adjustment negativo

Un ADJUSTMENT- chiude FIFO i lotti LONG con ricavo nullo.

padj=0p_{adj}=0 P&Ladj=−qcpopenlongP\&L_{adj} = -q_c p_{open}^{long}

Un Adjustment negativo non apre uno SHORT nella prima versione del sistema.

Se la quantità eccede i LONG disponibili, viene restituita una issue strutturata.

7. Transfer
7.1 Identificazione

Una coppia TRANSFER è composta da due transazioni collegate 1:1:

quantità negativa → broker sorgente
quantità positiva → broker destinatario


La direzione dipende dai segni, non dall’ordine delle date.

7.2 Intervallo di transito

Siano doutd_{out} e dind_{in} le date delle due gambe:

tstart=min⁡(dout,din)t_{start}=\min(d_{out},d_{in}) tend=max⁡(dout,din)t_{end}=\max(d_{out},d_{in})

L’intervallo di transito è:

[tstart,tend)[t_{start},t_{end})

Quindi:

data minore    → apertura del transito
date intermedie→ in transito
data maggiore  → custodia destinataria


Questa convenzione deve essere applicata anche al Portfolio Engine aggregato, correggendo l’attuale buco di valore nel giorno iniziale.

7.3 Transfer parziale

Il transfer seleziona FIFO i frammenti LONG presenti sul broker sorgente.

I frammenti:

mantengono lotto, data e prezzo originari;
entrano nello stato IN_TRANSIT;
vengono assegnati al destinatario alla fine dell’intervallo;
non generano cash;
non generano P&L;
ignorano il cost_basis_override nel dominio FIFO.

Esempio:

Lotto originario: 0,15 BTC su Coinbase
Transfer:         0,10 BTC verso IBKR

Tempo ───────────────────────────────────────────────────────────→

                                   start              end
                                     │                 │
Lotto BTC ●━━ Coinbase 0,15 ━━━━━━━━━┿━━━━━━━━━━━━━━━━━┿━━━━━━━
                                     │                 │
                                     ├━━ Coinbase 0,05 ━━━━━━━→
                                     │
                                     └══ Transit 0,10 ═╸
                                                       └━ IBKR
                                                          0,10 ━→

7.4 Limiti iniziali

Nella prima versione:

TRANSFER di frammenti LONG  → supportato
TRANSFER di posizione SHORT → issue esplicita, non supportato

8. Split e reverse split
8.1 Valenza algoritmica dell’evento

Un Adjustment collegato a un AssetEvent di tipo SPLIT non viene trattato come un normale Adjustment.

Lo split trasforma tutti i frammenti aperti dell’asset alla data dell’evento.

8.2 Trasformazione

Per rapporto r>0r>0:

qi(ts+)=r qi(ts−)q_i(t_s^+)=r\,q_i(t_s^-) pi0(ts+)=pi0(ts−)rp_i^0(t_s^+)=\frac{p_i^0(t_s^-)}{r}

L’invariante di costo è:

qi(ts+)pi0(ts+)=qi(ts−)pi0(ts−)q_i(t_s^+)p_i^0(t_s^+) = q_i(t_s^-)p_i^0(t_s^-)

Lo split:

non è retroattivo;
non modifica i dati antecedenti;
non crea un nuovo lotto;
non genera P&L;
trasforma soltanto quantità ancora aperte;
si applica anche ai frammenti in transito.
8.3 Esempio
Prima dello split:
10 quote @100

Split 2:1

Dopo lo split:
20 quote @50

                         SPLIT 2:1
                             │
Lotto A  ●━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━→
         10 @100             │ 20 @50


Il reverse split è la stessa trasformazione con:

0<r<10<r<1

Esempio:

20 @50
reverse split 1:2
10 @100

8.4 Ordinamento intraday

In assenza di orario, lo split si considera efficace all’inizio del giorno:

1. SPLIT;
2. altre transazioni ordinate per transaction_id.


Le operazioni registrate nella data dello split utilizzano quantità e prezzi post-split.

9. Valore e P&L dei lotti
9.1 Valore aperto
OpenValuei(t)=qiopen(t)⋅MarketPricea(t)OpenValue_i(t) = q_i^{open}(t)\cdot MarketPrice_a(t)

Per gli SHORT, il valore aperto rappresenta l’esposizione corrente, non un asset posseduto.

9.2 Incassi cumulati
Proceedsi(t)=∑SELL attribuiteal lotto ifino a tSellProceedsProceeds_i(t) = \sum_{\substack{SELL\ attribuite\\al\ lotto\ i\\fino\ a\ t}} SellProceeds

Gli Adjustment negativi non aumentano gli incassi.

9.3 Valore complessivo LONG
TotalValuei(t)=OpenValuei(t)+Proceedsi(t)TotalValue_i(t) = OpenValue_i(t)+Proceeds_i(t)

Il costo originario è:

OriginalCosti=qi0pi0OriginalCost_i=q_i^0p_i^0

Il P&L FIFO è:

P&Li(t)=TotalValuei(t)−OriginalCostiP\&L_i(t) = TotalValue_i(t)-OriginalCost_i
9.4 Selezione multipla

Per un insieme di lotti selezionati L\mathcal L:

OpenValueL(t)=∑i∈LOpenValuei(t)OpenValue_{\mathcal L}(t) = \sum_{i\in\mathcal L}OpenValue_i(t) ProceedsL(t)=∑i∈LProceedsi(t)Proceeds_{\mathcal L}(t) = \sum_{i\in\mathcal L}Proceeds_i(t) P&LL(t)=∑i∈LP&Li(t)P\&L_{\mathcal L}(t) = \sum_{i\in\mathcal L}P\&L_i(t)

Non viene imposto un limite tecnico al numero di lotti selezionati.

10. Stati derivati

Gli stati non costituiscono necessariamente un enum mutuamente esclusivo; descrivono proprietà derivate.

OPEN
PARTIALLY_CLOSED
CLOSED
IN_TRANSIT
DISTRIBUTED
LONG
SHORT
DEGRADED


Esempi:

OPEN + DISTRIBUTED + LONG
PARTIALLY_CLOSED + LONG
OPEN + SHORT
DEGRADED + OPEN


DEGRADED indica che parte della storia non è ricostruibile in modo affidabile.

11. Data Quality

Il nuovo endpoint restituisce il sistema esistente di DataQualityIssue.

Nuovi casi previsti:

REFERENCE_PRICE_FALLBACK
REFERENCE_PRICE_UNAVAILABLE
SHORT_TRANSFER_NOT_SUPPORTED
SHORT_ADJUSTMENT_NOT_SUPPORTED
FIFO_SOURCE_QUANTITY_MISSING
TRANSFER_PAIR_MISSING


La presenza di una issue non impedisce necessariamente di restituire la parte ricostruibile.

status = COMPLETE | DEGRADED | UNAVAILABLE

12. Architettura
12.1 Suddivisione delle responsabilità
┌───────────────────────────────────────────────────────────────────┐
│ TRANSACTION LOG                                                   │
│ BUY · SELL · ADJUSTMENT · TRANSFER · AssetEvent                   │
└──────────────────────────────┬────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌──────────────────────────┐       ┌───────────────────────────────┐
│ PORTFOLIO ENGINE         │       │ FIFO LOT ENGINE               │
│                          │       │                               │
│ Quantità aggregate       │       │ Lotti LONG/SHORT              │
│ NAV / Book Value         │       │ Chiusure FIFO                 │
│ WAC broker/cumulato      │       │ Frammenti di custodia         │
│ Performance              │       │ Transito e biforcazioni       │
│ K/R/W                    │       │ P&L per lotto                 │
└──────────────┬───────────┘       └───────────────┬───────────────┘
               │                                   │
               └─────────────────┬─────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE                                             │
│                                                                   │
│ Query bulk transazioni                                            │
│ Risoluzione transfer pair                                         │
│ Price service                                                     │
│ FX service                                                        │
│ WAC history                                                       │
│ Data Quality                                                      │
│ Assemblaggio DTO                                                  │
└──────────────────────────────┬────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ POST /portfolio/lots/analysis                                     │
│ Richiesta bulk multi-analysis                                     │
└──────────────────────────────┬────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                          │
│ WAC chart · Gantt · DataTable · Modale · Confronto                │
└───────────────────────────────────────────────────────────────────┘

12.2 FifoLotEngine

Responsabilità:

classificazione degli eventi;
code FIFO LONG e SHORT;
apertura e chiusura dei lotti;
fragment identity;
custodia e transito;
trasformazioni SPLIT;
P&L FIFO;
issue matematiche.


Caratteristiche:

puro;
senza I/O;
deterministico;
testabile con eventi sintetici;
indipendente dalla UI;
indipendente da share_percentage.

12.3 LotsAnalysisService

Responsabilità:

caricamento bulk delle transazioni;
accesso al service layer prezzi;
accesso al service layer FX;
richiesta delle serie WAC;
esecuzione del FifoLotEngine;
conversione nella target currency;
costruzione delle analisi richieste;
produzione DataQuality.


Il service evita:

una query per lotto;
una query per giorno;
una query per broker e punto prezzo.

13. API bulk
13.1 Endpoint
POST /portfolio/lots/analysis

13.2 Request concettuale
asset_id
broker_ids
date_from
date_to
target_currency
selected_lot_ids
requested_analyses


Analisi richiedibili:

LOT_SUMMARY
GANTT_TOPOLOGY
CUSTODY_HISTORY
EVENT_HISTORY
VALUE_HISTORY
RETURN_HISTORY
PRICE_HISTORY
BROKER_WAC_HISTORY
CUMULATIVE_WAC_HISTORY


Una richiesta può richiedere più analisi contemporaneamente.

13.3 Response concettuale
asset
target_currency
calculation_status
calculation_metadata
data_quality

lots[]
custody_segments[]
lot_events[]
histories[]
wac_series[]


Tutti i valori monetari sono restituiti nella target_currency.

Il frontend non effettua autonomamente:

conversioni FX;
attribuzioni FIFO;
caricamenti separati dei prezzi;
calcoli WAC.
14. Interfaccia grafica
14.1 Struttura generale
┌────────────────────────────────────────────────────────────────────┐
│ ASSET HEADER                                                       │
│ [icon] Nome · simbolo · quantità · valore · broker                 │
├────────────────────────────────────────────────────────────────────┤
│ WAC / PREZZO DI MERCATO                                            │
├────────────────────────────────────────────────────────────────────┤
│ GANTT — VITA E CUSTODIA DEI LOTTI                                 │
├────────────────────────────────────────────────────────────────────┤
│ TABELLA UNIFICATA DEI LOTTI                                       │
├────────────────────────────────────────────────────────────────────┤
│ CONFRONTO DEI LOTTI SELEZIONATI                                   │
│ [Valore] [Rendimento] [Prezzo]                                    │
└────────────────────────────────────────────────────────────────────┘

14.2 WAC e prezzo di mercato
┌────────────────────────────────────────────────────────────────────┐
│ WAC / Prezzo di mercato                     [Assoluto] [%]         │
│                                                                    │
│ 160 ┤                                        ╭──── Prezzo mercato │
│ 140 ┤                              ╭─────────╯                     │
│ 120 ┤──────── WAC cumulato ────────╯                               │
│ 100 ┤         ┌──── WAC Directa ─────────────                     │
│  80 ┤─────────┘                                                    │
│  60 ┤                    ┌──── WAC IBKR ─────────────              │
│     └────────────────────────────────────────────────────────────  │
│      feb       mar       apr       mag       giu       lug        │
└────────────────────────────────────────────────────────────────────┘


Serie:

Prezzo di mercato
WAC broker
WAC cumulato, se almeno due broker detengono l’asset


La label Market Price deve essere localizzata in tutte le lingue.

14.3 Gantt

Ogni lane corrisponde a un lotto.

┌─────────────────────────────────────────────────────────────────────┐
│ Vita e custodia dei lotti                   [Aperti] [Tutti]        │
│                                                                     │
│ [asset] Lotto 17/02  ●━━━━ Directa · 2 ━━━━━━━━━━━━━━━━━━━━━━━→    │
│                                                                     │
│ [asset] Lotto 04/03       ●━━━━ Directa · 2 ━━━━━━━━━━━━━━━━━→     │
│                                                                     │
│ [asset] Lotto BTC    ●━━━━ Coinbase · 0,15 ━┳━ Coinbase 0,05 →     │
│                                             └══ Transit ══ IBKR →  │
│                                                                     │
│                     [────── zoom temporale condiviso ──────]        │
└─────────────────────────────────────────────────────────────────────┘


Codifica:

spessore       quantità del frammento
colore         broker
tratteggio     in transito
opacità        stato aperto/storico
bordo/glow     selezione
icona asset    lane
icona broker   segmento di custodia

14.4 Spessore

Sia:

Qmax⁡=max⁡iqi0Q_{\max}=\max_i q_i^0

Lo spessore è:

Thickness(q)=Tmin⁡+qQmax⁡(Tmax⁡−Tmin⁡)Thickness(q)= T_{\min} + \frac{q}{Q_{\max}} (T_{\max}-T_{\min})
Quantità massima  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quantità media    ━━━━━━━━━━━━━━━━━━━
Quantità minima   ━━━━━
Quantità zero     assente

14.5 Opacità fissa
ramo aperto       90%
in transito       65% + tratteggio
ramo chiuso       45%
fuori dal range   assente


La selezione non modifica l’opacità degli altri elementi.

Il lotto selezionato utilizza:

bordo
glow
marker accentuato
pulse temporaneo

14.6 Tabella unificata
┌─────────────────────────────────────────────────────────────────────────┐
│ Lotti                             [Stato ▾] [Broker ▾] [Cerca...]       │
├───┬────────────┬─────────┬──────────────┬──────────┬─────────┬──────────┤
│   │ Apertura   │ Dir.    │ Stato        │ Custodia │ Q.tà    │ P&L FIFO│
├───┼────────────┼─────────┼──────────────┼──────────┼─────────┼──────────┤
│ ☑ │ 17/02/2025 │ LONG    │ Aperto       │ Directa  │ 2       │ +121,58 │
│ ☑ │ 04/03/2025 │ LONG    │ Parziale     │ Directa  │ 1 / 2   │  +68,92 │
│ ☐ │ 01/04/2025 │ LONG    │ Chiuso       │ —        │ —       │  +72,25 │
│ ☑ │ 18/06/2026 │ LONG    │ Distribuito  │ 2 broker │ 0,15 BTC│ ...      │
│ ☐ │ 10/07/2026 │ SHORT   │ Aperto       │ IBKR     │ 3       │ ...      │
└───┴────────────┴─────────┴──────────────┴──────────┴─────────┴──────────┘


Terminologia neutra:

Data apertura
Prezzo apertura
Direzione


anziché esclusivamente:

Data acquisto
Prezzo acquisto

14.7 Modale Custodia

Il click sulla cella Custodia apre la modale.

┌──────────────────────────────────────────────────────────────────┐
│ [asset] Lotto Bitcoin — 18 giugno 2026                       [X] │
├──────────────────────────────────────────────────────────────────┤
│ RIEPILOGO                                                        │
│ Direzione             LONG                                      │
│ Quantità originaria   0,150000 BTC                              │
│ Quantità aperta       0,150000 BTC                              │
│ Prezzo apertura       1.333,33 €/BTC                            │
│ Stato                 Distribuito                               │
├──────────────────────────────────────────────────────────────────┤
│ CUSTODIA ATTUALE                                                 │
│ [Coinbase] Coinbase   0,100000 BTC                              │
│ [IBKR]     IBKR       0,050000 BTC                              │
├──────────────────────────────────────────────────────────────────┤
│ CRONOLOGIA                                                       │
│ 18/06 ● BUY Coinbase                         +0,150000 BTC       │
│ 06/07 ⇄ Coinbase → In transito               0,100000 BTC       │
│ 08/07 ⇄ In transito → IBKR                   0,100000 BTC       │
│ 10/07 ⇄ IBKR → Coinbase                      0,050000 BTC       │
├──────────────────────────────────────────────────────────────────┤
│                            [Chiudi] [Vai alla transazione]        │
└──────────────────────────────────────────────────────────────────┘

14.8 Interazioni Gantt–tabella
Click riga
→ selezione multipla
→ aggiorna grafico comparativo

Click Custodia
→ apre modale

Doppio click riga
→ scroll al lotto nel Gantt
→ pulse

Doppio click Gantt
→ scroll alla riga
→ pulse

┌───────────────┐           ┌───────────────────┐
│ DataTable     │◄─────────►│ Gantt             │
│ selected IDs  │  sync     │ highlighted lots  │
└───────┬───────┘           └─────────┬─────────┘
        │                             │
        ▼                             ▼
┌───────────────────┐       ┌────────────────────┐
│ Grafico confronto │       │ Modale Custodia   │
└───────────────────┘       └────────────────────┘

15. Grafico comparativo

Il grafico contiene tutti i lotti selezionati.

┌─────────────────────────────────────────────────────────────────────┐
│ 4 lotti selezionati              [Valore] [Rendimento] [Prezzo]    │
│                                                                     │
│ ☑ Lotto 17/02                                                   │
│ ☑ Lotto 04/03                                                   │
│ ☑ Lotto BTC                                                     │
│ ☑ Short 10/07                                                   │
└─────────────────────────────────────────────────────────────────────┘

15.1 Modalità Valore
┌────────────────────────────────────────────────────────────────────┐
│ Valore dei lotti selezionati                                      │
│                                                                    │
│ 900 € ┤                            █████ Incassi cumulati          │
│ 750 € ┤                  ▓▓▓▓▓▓▓▓▓▓▓▓▓ Valore residuo             │
│ 600 € ┼──────── Costo originario complessivo ──────────────────   │
│ 450 € ┤        ▓▓▓▓▓▓▓▓                                           │
│ 300 € ┤  ▓▓▓▓▓▓                                                     │
│   0 € ┼─────────────────────────────────────────────────────────   │
└────────────────────────────────────────────────────────────────────┘

15.2 Modalità Rendimento
┌────────────────────────────────────────────────────────────────────┐
│ Rendimento dalla data di apertura                                 │
│                                                                    │
│ 180% ┤                      ╭──── Lotto 04/03                      │
│ 150% ┤             ╭────────╯                                      │
│ 120% ┤      ╭──────╯       ╭──── Lotto 17/02                      │
│  90% ┤  ╭───╯      ╭────────╯                                      │
│   0% ┼──●──────────●────────────────────────────────────────────  │
└────────────────────────────────────────────────────────────────────┘


Per ADJUSTMENT+, il riferimento relativo è il prezzo alla ricezione, mentre il costo cash FIFO resta zero.

15.3 Modalità Prezzo
┌────────────────────────────────────────────────────────────────────┐
│ Prezzo e costo medio                                               │
│                                                                    │
│ 160 ┤                                  ╭──── Prezzo di mercato     │
│ 140 ┤                         ╭────────╯                            │
│ 120 ┼──── Prezzo apertura Lotto A ─────────────────────────────   │
│ 100 ┼──── Prezzo apertura Lotto B ─────────────────────────────   │
│  90 ┤          ┌──── WAC cumulato ─────────────────────────       │
│  70 ┤    ┌──── WAC Directa                                       │
│  60 ┤    └──────── WAC IBKR ─────────────────────────────         │
└────────────────────────────────────────────────────────────────────┘


Visibili inizialmente:

Prezzo di mercato
Prezzi di apertura
WAC cumulato


I WAC dei singoli broker sono disponibili tramite legenda.

16. Sincronizzazione temporale

WAC e Gantt condividono sempre:

range
zoom
pan
crosshair

┌───────────────────────────────────────────────────────────────┐
│ WAC / Prezzo      │<──── intervallo temporale ────────────>| │
├───────────────────────────────────────────────────────────────┤
│ Gantt             │<──── intervallo temporale ────────────>| │
└───────────────────────────────────────────────────────────────┘
                       [──── slider comune ────]


Il grafico comparativo utilizza inizialmente lo stesso range, ma possiede zoom indipendente.

17. Range di calcolo e visualizzazione

Il motore ricostruisce gli eventi dall’inizio della storia fino a date_to.

CalculationRange=[tinception,dateto]CalculationRange= [t_{inception},date_{to}]

Il frontend visualizza soltanto:

DisplayRange=[datefrom,dateto]DisplayRange= [date_{from},date_{to}]

Un lotto iniziato prima del range appare clippato:

←━━━━ Directa · 2 quote ━━━━━━━━━━━━━━━━━━━━━→


Un lotto completamente chiuso prima del range non viene renderizzato.

18. Evoluzione dei componenti
Da mantenere
Portfolio Engine
WAC per broker e cumulato
service layer prezzi
service layer FX
DataTable
helper ECharts dataZoom
DataQuality framework
i18n audit

Da modificare
AssetWacPriceChart
FIFOLotsPanel
loader transazioni multi-broker
gestione WAC di split/reverse split
API portfolio

Da creare
FifoLotEngine
LotsAnalysisService
POST /portfolio/lots/analysis
DTO bulk
Gantt
tabella unificata
modale Custodia
grafico comparativo
supporto LONG/SHORT FIFO

Da rimuovere dopo migrazione
get_lots() attuale
calculate_fifo_lots() come percorso pubblico
get_asset_history() nella forma attuale
BubbleLotTimeline
OpenLotsTable
ClosedLotsTable

19. Implementazione progressiva
Fase 0 — prerequisiti
uniformare il transito a [min,max);
correggere WAC per split e reverse split;
fissare DTO direction-neutral;
definire identity degli eventi e dei frammenti.

Fase 1 — motore puro
BUY/SELL LONG e SHORT
ADJUSTMENT±
TRANSFER LONG
SPLIT/reverse split
P&L FIFO
Data Quality
test matematici

Fase 2 — service e API
loader bulk;
prezzi e FX;
serie WAC;
target currency;
endpoint multi-analysis.

Fase 3 — frontend
Gantt;
tabella unificata;
modale;
grafico comparativo;
sincronizzazione temporale.

Fase 4 — migrazione e pulizia
rimozione vecchi endpoint/componenti;
i18n;
gallery;
E2E;
benchmark;
valutazione cache backend.

20. Nota obbligatoria di verifica sul WAC

Prima dell’implementazione operativa deve essere verificato formalmente che l’attuale algoritmo WAC restituisca un costo medio unitario riferito a una singola unità intera dell’asset, e non il costo complessivo della quantità acquistata.

Per acquisizioni kk:

WAC=∑kqkpk∑kqkWAC= \frac{\sum_k q_k p_k} {\sum_k q_k}

dove pkp_k è il prezzo unitario:

pk=∣Ak∣qkp_k= \frac{|A_k|}{q_k}

Esempio:

q=0,15 BTCq=0{,}15\ BTC A=−200 EURA=-200\ EUR

Il prezzo unitario corretto è:

p=2000,15=1.333,33 EUR/BTCp= \frac{200}{0{,}15} = 1.333{,}33\ EUR/BTC

e non:

200 EUR/BTC200\ EUR/BTC

Il costo complessivo resta:

0,15×1.333,33=2000{,}15\times1.333{,}33 = 200

La verifica deve coprire almeno:

Portfolio Engine inline WAC
compute_wac_from_txlist
compute_wac_iterative
endpoint WAC
AssetWacPriceChart
transfer cost_basis_override
BUY con quantità frazionaria
ADJUSTMENT positivo
conversioni FX
formatter frontend


Se uno dei sistemi tratta erroneamente l’ammontare totale come costo unitario, la correzione deve essere applicata in modo coerente a tutti i percorsi interessati, accompagnata da test di regressione comuni.

Il nuovo FifoLotEngine deve applicare senza ambiguità:

opening_unit_price=∣amount∣∣quantity∣opening\_unit\_price = \frac{|amount|}{|quantity|}

per ogni BUY o SELL che apre una posizione.
