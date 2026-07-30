Sì, qui conviene essere molto prescrittivi: stessa formula già approvata, matrice esatta delle 18 combinazioni, regola eventi lineare e nessun ranking. Il report successivo dovrà misurare non solo token e righe, ma anche le fasce temporali effettive prodotte da ogni classe.

# AI Export: granularità temporale per classe di segnale, selezione eventi e documentazione tecnica

Usa il codice corrente come source of truth e leggi integralmente almeno:

- `report-phase00AiExportRuntimeDeepAudit.md`
- `report-phase00AiExportSizeAndTechnicalDensity.md`
- `probe-phase00AiExportTechnicalDensity.json`
- la Developer Guide corrente dell’AI Export;
- l’implementazione runtime del sampling adattivo;
- il catalogo dei dataset e delle analisi;
- i Signal Plugin e le annotation effettivamente registrate.

Questa attività deve:

1. implementare la granularità temporale degli indicatori dipendente sia dal livello di dettaglio sia dalla classe temporale del segnale;
2. implementare la nuova selezione deterministica degli eventi;
3. aggiornare la documentazione tecnica dell’AI Export;
4. eseguire probe dimensionali e temporali completi;
5. produrre un nuovo report per permettere un ulteriore fine tuning.

Non cambiare la granularità dei prezzi.  
Non reintrodurre Drawdown Recovery.  
Non introdurre segmentazione dell’export.  
Non introdurre troncamenti basati su token o caratteri.  
Non inventare formule, parametri o politiche diverse da quelle definite qui.

---

# 1. Separazione delle responsabilità

Mantieni separate queste due dimensioni:

```text
Detail level
→ precisione massima scelta dall’utente

Signal temporal class
→ riduzione relativa appropriata alla velocità del segnale


Un segnale non deve mai essere esportato con maggiore precisione rispetto alla griglia attuale del detail selezionato.

La classe più veloce deve quindi coincidere con la precisione attuale:

Very Fast + Compact  = Compact attuale
Very Fast + Standard = Standard attuale
Very Fast + Full     = Full attuale


Tutte le classi successive devono avere una densità monotonicamente inferiore:

Very Fast
> Fast
> Medium Fast
> Medium
> Slow
> Very Slow


Per ogni classe deve inoltre valere:

Full > Standard > Compact


Il sistema deve continuare a esportare:

tutti gli asset applicabili;
tutti gli indicatori calcolabili richiesti dal profilo;
tutti gli output dell’indicatore;
summary e latest state dell’intero periodo;
eventi secondo la policy definita più avanti.

Cambia solo la densità della storia numerica degli indicatori.

2. Formula obbligatoria

Usa esattamente la funzione razionale già adottata dal progetto.

Siano:

x: distanza in giorni da snapshot_as_of;
P: parametro di forma;
M: punto di metà transizione;
K: intervallo massimo asintotico del bucket, in giorni;
T: durata totale richiesta, in giorni.

La funzione continua è:

f(x;P,M,K)=1+(K−1)max⁡(x−7,0)PMP+max⁡(x−7,0)Pf(x;P,M,K) = 1+(K-1) \frac{\max(x-7,0)^P} {M^P+\max(x-7,0)^P}

Il delta intero è:

D(x;P,M,K)=max⁡(1,round⁡half-up[f(x;P,M,K)])D(x;P,M,K) = \max \left( 1, \operatorname{round}_{half\text{-}up} \left[ f(x;P,M,K) \right] \right)

La costruzione iterativa dei confini è:

x0=0x_0=0 xn+1=min⁡(T,xn+D(xn;P,M,K))x_{n+1} = \min \left( T, x_n+D(x_n;P,M,K) \right)

Ogni intervallo:

[xn,xn+1][x_n,x_{n+1}]

genera un bucket.

Vincoli obbligatori
Per:
0≤x≤70 \le x \le 7

deve risultare:

D(x)=1D(x)=1

Gli ultimi sette giorni devono quindi restare sempre a precisione giornaliera per:

ogni detail;
ogni temporal class;
ogni indicatore.

Il delta deve essere:

intero;
positivo;
monotonicamente non decrescente rispetto a x;
sempre minore o uguale a K.

L’ultimo bucket deve terminare esattamente a T.

Non devono esistere:

bucket nulli;
overlap;
gap tra bucket;
bucket oltre il periodo richiesto.

Usa una funzione esplicita di round half-up per numeri positivi. Non affidarti implicitamente al banker's rounding del linguaggio se produce risultati differenti.

Non sostituire questa formula con:

crescita lineare;
Weibull;
logistica;
Gompertz;
campionamento fixed weekly/monthly;
ultimi N punti;
sampling legacy 7 daily + 8 weekly.
3. Matrice dei parametri

Implementa inizialmente la seguente matrice.

Compact
Very Fast:
P = 2
M = 30
K = 30

Fast:
P = 2
M = 25
K = 35

Medium Fast:
P = 2
M = 20
K = 42

Medium:
P = 2
M = 10
K = 42

Slow:
P = 2
M = 5
K = 49

Very Slow:
P = 2
M = 5
K = 84


Conteggi di riferimento:

                 90d   180d   365d
Very Fast        20     23      29
Fast             18     21      26
Medium Fast      16     18      23
Medium           14     16      20
Slow             12     14      17
Very Slow        11     12      14

Standard
Very Fast:
P = 2
M = 30
K = 14

Fast:
P = 2
M = 21
K = 15

Medium Fast:
P = 2
M = 20
K = 17

Medium:
P = 2
M = 15
K = 20

Slow:
P = 2
M = 10
K = 22

Very Slow:
P = 2
M = 5
K = 28


Conteggi di riferimento:

                 90d   180d   365d
Very Fast        26     33      46
Fast             23     29      41
Medium Fast      21     26      37
Medium           18     23      32
Slow             16     20      28
Very Slow        13     16      23

Full
Very Fast:
P = 2
M = 30
K = 7

Fast:
P = 2
M = 28
K = 8

Medium Fast:
P = 2
M = 23
K = 9

Medium:
P = 2
M = 16
K = 10

Slow:
P = 2
M = 10
K = 11

Very Slow:
P = 2
M = 9
K = 14


Conteggi di riferimento:

                 90d   180d   365d
Very Fast        35     49      75
Fast             32     44      67
Medium Fast      28     38      59
Medium           24     33      51
Slow             21     29      46
Very Slow        18     24      38

Osservazione sui conteggi

I conteggi sopra derivano da:

periodi esatti di 90, 180 e 365 giorni;
iterazione a partire da x=0;
formula indicata;
round half-up;
ultimo bucket tagliato esattamente a T.

Prima di modificare i test, esegui una verifica indipendente nel runtime reale.

Se i conteggi differiscono:

non correggere arbitrariamente i parametri;
verifica:
estremi inclusivi o esclusivi;
significato di T;
round usato;
offset della settimana iniziale;
ordine del calcolo;
taglio dell’ultimo bucket;
documenta la causa;
mantieni la formula e la semantica espresse in questa specifica;
riporta nel report sia il conteggio teorico sia quello runtime.
4. Contratto della classe temporale

Estendi il contratto comune degli indicatori o Signal Plugin affinché ogni istanza possa dichiarare una classe temporale AI Export.

Usa un enum tipizzato equivalente a:

VERY_FAST
FAST
MEDIUM_FAST
MEDIUM
SLOW
VERY_SLOW


Il plugin deve dichiarare solo la classe semantica.

Il plugin non deve conoscere:

Compact;
Standard;
Full;
i parametri numerici P, M, K;
la formula;
il numero di bucket;
il periodo dell’export.

La policy centrale AI Export deve risolvere:

detail_level + temporal_class
→ P, M, K


Evita:

if signal_code == "EMA200"


o altri branch per indicatore dentro sampler, serializer o assembler.

La classe deve essere:

deterministica;
versionabile;
leggibile dal catalogo runtime;
ispezionabile nei test;
disponibile nella documentazione diagnostica;
associata al plugin come source of truth.

Se il progetto distingue indicatore e signal plugin, colloca la proprietà nel livello architetturale che possiede realmente la produzione della serie numerica e documenta la scelta.

5. Classificazione iniziale degli indicatori

Usa inizialmente questa classificazione.

Very Fast
StochRSI
RSI
MFI

Fast
CCI
ROC
ATR
NATR

Medium Fast
MACD
PPO
Bollinger
Donchian

Medium
EMA20
KAMA20
Aroon
ADX
OBV

Slow
EMA50
SMA50

Very Slow
EMA200
SMA200


Applica la classificazione alle istanze Asset e FX realmente disponibili.

Non aggiungere indicatori non presenti.

Se un plugin produce più istanze con periodi sostanzialmente differenti, la classe può essere dichiarata:

dall’istanza;
dalla configurazione registrata;
oppure risolta dal plugin sulla base dei parametri.

Non duplicare però la classificazione nel catalogo AI Export se il plugin può esserne source of truth.

Questa classificazione è iniziale e dovrà essere sottoposta ai probe. Non modificarla autonomamente in base a preferenze qualitative. Eventuali proposte alternative devono comparire nel report, non essere applicate senza evidenza.

6. Bucket indicatori

Per ogni indicatore:

calcola l’indicatore sulla serie observation-level completa necessaria;
usa il calculation range richiesto dal warm-up;
rileva stati ed eventi sulla serie observation-level, non sui bucket;
taglia l’output al periodo AI;
applica alla storia numerica la policy:
detail;
temporal class;
matrice P/M/K;
preserva per ogni bucket, quando applicabile:
start date;
end date;
first;
minimum;
minimum date;
maximum;
maximum date;
last;
observation count;
preserva summary e latest state dell’intero periodo.

Per indicatori multi-output come:

MACD;
PPO;
Bollinger;
Donchian;
Aroon;
StochRSI;
ADX, secondo gli output reali;

usa gli stessi confini temporali per tutti gli output della stessa istanza.

Non creare una griglia differente per ogni colonna della stessa istanza.

La granularità degli indicatori non deve modificare:

rilevazione dei cross;
timestamp degli eventi;
latest state;
estremi globali del periodo;
warm-up;
applicabilità;
validazione input/output.
7. Prezzi e FX rate

Non applicare le temporal class dei segnali a:

prezzi Asset;
rate FX;
serie fondamentali equivalenti.

Prezzi e rate devono continuare a usare esclusivamente la policy corrente del detail:

Compact  → P=2, M=30, K=30
Standard → P=2, M=30, K=14
Full     → P=2, M=30, K=7


La motivazione è che prezzi e rate sono la traiettoria di riferimento rispetto alla quale interpretare indicatori, stati ed eventi.

8. Nuova policy degli eventi

Implementa una policy indipendente per ogni:

entity_id + annotation_key


Dove:

per Asset, entity_id identifica l’asset;
per FX, identifica la coppia canonica;
per aggregati Portfolio/Broker, gli eventi devono conservare l’identità dell’asset originario e applicare la policy prima dell’unione finale;
annotation_key identifica esattamente la coppia, soglia o rilevatore, per esempio:
ema_50_ema_200;
stoch_rsi_k_d;
rsi_14_overbought_70;
price_bollinger_upper.
Regola esatta

Per ogni gruppo:

ordina gli eventi dal più recente al più vecchio;
includi tutti gli eventi con:
event_date >= snapshot_as_of - 30 giorni di calendario

se gli eventi inclusi sono meno di 20:
continua linearmente all’indietro;
aggiungi gli eventi immediatamente precedenti;
fermati quando il totale raggiunge 20;
se il gruppo contiene meno di 20 eventi nell’intero periodo, includili tutti;
se gli ultimi 30 giorni contengono più di 20 eventi, includili tutti;
non applicare un limite massimo ulteriore;
non usare ranking;
non distribuire gli eventi storici uniformemente;
non creare campioni per famiglia;
non consolidare gli eventi in episodi;
non cambiare l’ordine cronologico finale previsto dal formato pubblico.

Formalmente, sia:

recent_count = numero eventi negli ultimi 30 giorni
total_count  = numero eventi nel periodo


allora:

exported_count =
    min(
        total_count,
        max(20, recent_count)
    )


Gli eventi esportati devono essere i primi exported_count eventi dopo l’ordinamento dal più recente al più vecchio.

Esempi obbligatori nei test
total=8, recent=3
→ exported=8

total=30, recent=4
→ exported=20

total=50, recent=12
→ exported=20

total=50, recent=25
→ exported=25

total=200, recent=40
→ exported=40

Inclusività temporale

Definisci e documenta esplicitamente la semantica del giorno limite:

event_date >= snapshot_as_of - 30 calendar days


Usa la stessa timezone/date semantics già adottata dallo snapshot.

Non usare 30 sessioni di mercato. La regola è su 30 giorni di calendario.

9. Statistiche della selezione eventi

Affinché l’LLM sappia se l’elenco è completo o selezionato, serializza per ciascun gruppo almeno:

annotation_key: ...
detected_count: ...
recent_30d_count: ...
exported_count: ...
selection_applied: ...
oldest_detected_event_date: ...
newest_detected_event_date: ...
oldest_exported_event_date: ...
newest_exported_event_date: ...


Aggiungi, se già determinabili senza ambiguità:

upward_count: ...
downward_count: ...


Non inserire:

relevance score;
severity inventata;
ranking finanziario;
interpretazione buy/sell;
motivazioni probabilistiche.

Il filtro deve essere applicato dopo:

validazione;
observed-only;
epsilon;
gap rules;
deduplicazione semantica esistente;

e prima della serializzazione finale.

Gli eventi devono continuare a provenire dalle osservazioni originali, non dai bucket compressi.

10. Relazione tra dettaglio e selezione eventi

Per la prima implementazione, la policy degli eventi deve essere uguale in:

Compact;
Standard;
Full.

Quindi il detail modifica:

prezzi;
storia numerica degli indicatori;

ma non modifica:

ultimi 30 giorni completi di eventi;
minimo degli ultimi 20 eventi per annotation key;
summary degli eventi.

Questo permette di studiare separatamente:

peso della densità numerica
peso della selezione eventi


Non introdurre ora soglie eventi differenti per detail.

11. Aggiornamento della Developer Guide

Aggiorna la sezione della Developer Guide dedicata alla creazione e composizione dei prompt AI Export.

Non concentrare tutto in una pagina monolitica. Se la pagina esistente è già troppo ampia, dividila in pagine collegate e aggiorna la navigazione.

La documentazione deve descrivere almeno i seguenti argomenti.

11.1 Mattoncini interni

Spiega:

differenza tra componente granulare, dataset composto e analisi;
responsabilità dei componenti;
come un dataset dichiara i componenti richiesti e opzionali;
come all_data unisce i dataset senza un builder monolitico;
come le analisi dichiarano dataset required e optional;
come avviene la deduplicazione;
applicabilità per:
Dashboard;
Broker;
Asset;
FX.

Includi un diagramma concettuale equivalente a:

Sources and engines
    → granular components
    → composed datasets
    → data-only export

Sources and engines
    → granular components
    → composed datasets
    → analysis profile
    → instructions and response contract
    → full prompt

11.2 Composizione del prompt

Documenta l’ordine effettivo:

Analysis Objective;
Shared Verification Instructions;
Response Contract;
Snapshot Metadata and Dataset Manifest;
Snapshot Data;
Additional LibreFolio Data;
Domain Notes;
User Notes;
Response Language.

Spiega:

quali sezioni esistono solo per Request Analysis;
quali esistono per Export Data;
come vengono risolti i dataset optional;
cosa succede quando manca un required;
cosa succede quando manca un optional;
successo parziale dei componenti disaccoppiati;
omissione dei singoli indicatori non calcolabili;
failure semantics e manifest.

La documentazione deve descrivere il comportamento reale del runtime dopo questa modifica, non soltanto il disegno teorico.

11.3 Sampling temporale

Documenta separatamente:

Prezzi e rate

Usano soltanto il detail.

Indicatori

Usano:

detail + temporal class


Includi:

formula completa;
significato di x, P, M, K, T;
round half-up;
iterazione dei confini;
settimana recente giornaliera;
matrice completa delle 18 combinazioni;
conteggi di riferimento 90/180/365 giorni;
differenza tra calculation range ed exported range;
warm-up;
summary/latest rispetto alla storia bucketizzata;
indicatori multi-output;
eventi rilevati prima del sampling.
Eventi

Documenta:

ultimi 20 eventi per entity + annotation key,
oppure tutti gli eventi degli ultimi 30 giorni
se questi sono più di 20


Spiega chiaramente che:

gli eventi vengono ordinati dal più recente;
non esiste ranking;
non esiste sampling distribuito;
gli eventi recenti possono superare 20;
l’LLM riceve i conteggi completi della selezione;
gli eventi non vengono rilevati sui bucket.
11.4 Estensione dei plugin

Documenta come un developer deve:

aggiungere un nuovo indicatore;
dichiarare la temporal class;
fornire requisiti e warm-up;
validare input e output;
fornire la descrizione AI;
dichiarare stati e annotation;
aggiungere test;
verificare la posizione nella matrice detail/class;
evitare dipendenze dirette dell’AI Export dal signal code.
12. Test obbligatori
12.1 Formula e matrice

Aggiungi test parametrizzati per tutte le 18 combinazioni:

3 detail × 6 temporal class


Verifica:

parametri risolti;
delta nei primi sette giorni;
monotonicità;
upper bound K;
conteggi a 90, 180 e 365 giorni;
copertura completa;
ultimo bucket esatto;
nessun gap;
nessun overlap;
determinismo;
periodi inferiori a sette giorni;
Custom molto lungo.
12.2 Ordinamento delle densità

Verifica esplicitamente:

Very Fast >= Fast >= Medium Fast >= Medium >= Slow >= Very Slow


per ciascun detail e ciascun periodo testato.

Verifica:

Full >= Standard >= Compact


per ciascuna temporal class.

La classe Very Fast deve avere gli stessi conteggi della baseline attuale.

12.3 Plugin

Verifica:

temporal class presente per ogni indicatore esportabile;
nessun fallback silenzioso non documentato;
errore chiaro per classi sconosciute;
classificazione delle istanze Asset e FX;
indicatori multi-output con confini condivisi.

Se serve un fallback per compatibilità interna, deve essere:

tipizzato;
esplicito;
coperto da test;
riportato nel manifest diagnostico;
non utilizzato dai plugin ufficiali.
12.4 Eventi

Testa:

esempi numerici definiti sopra;
esattamente 20;
zero eventi;
meno di 20;
più di 20 ma meno di 20 recenti;
più di 20 recenti;
evento esattamente sul limite dei 30 giorni;
ordinamento;
più annotation sullo stesso asset;
stesso annotation su asset differenti;
Portfolio e Broker con stesso asset su broker multipli;
FX;
observed-only;
epsilon;
deduplicazione;
indipendenza dal detail.
13. Probe richiesti

Dopo l’implementazione, ripeti i probe su dataset reale e salva un nuovo file machine-readable.

Percorso suggerito:

LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
probe-phase00AiExportSignalDensityV2.json

13.1 Matrice dimensionale generale

Esegui almeno:

Scope:
- Asset
- Broker
- Portfolio
- FX, se il coupling del warm-up consente l’esecuzione

Period:
- 3M
- 6M
- 1Y

Detail:
- Compact
- Standard
- Full


Per ogni probe riporta:

request completa;
periodo effettivo;
asset;
posizioni;
broker;
indicatori richiesti;
indicatori esportati;
temporal class per indicatore;
numero bucket di prezzo;
numero bucket per indicatore;
eventi rilevati;
eventi esportati;
caratteri;
byte UTF-8;
token stimati;
esito HTTP/runtime.
13.2 Fasce temporali

Per ogni combinazione:

detail + temporal class + periodo


riporta:

tutti i confini dei bucket;
ampiezza di ogni bucket;
prima data non giornaliera;
numero effettivo di bucket giornalieri iniziali;
distanza alla quale il delta raggiunge:
2 giorni;
3 giorni;
5 giorni;
7 giorni;
14 giorni, se applicabile;
il relativo K;
ampiezza massima effettivamente raggiunta nel periodo;
rapporto tra bucket esportati e giorni del periodo.

Non limitarti ai conteggi finali. Serve vedere la distribuzione temporale per effettuare il fine tuning.

13.3 Peso per classe e indicatore

Per ogni indicatore riporta:

temporal class;
P/M/K risolti per detail;
output count;
bucket count;
caratteri;
token stimati;
percentuale del blocco indicatori;
percentuale del payload;
confronto con la baseline precedente;
riduzione assoluta e percentuale.

Evidenzia separatamente gli indicatori multi-output:

Bollinger;
ADX;
MACD;
PPO;
Donchian;
Aroon;
StochRSI.
13.4 Eventi

Per ogni:

entity_id + annotation_key


riporta:

detected count;
recent 30-day count;
exported count;
omitted count;
first and last detected date;
first and last exported date;
caratteri prima;
caratteri dopo;
riduzione percentuale.

Aggrega poi per:

plugin;
asset;
annotation key;
famiglia;
scope.

Evidenzia almeno:

stoch_rsi_k_d;
StochRSI 20/80;
MACD/signal;
MACD histogram/zero;
prezzo/EMA20;
EMA20/EMA50;
EMA50/EMA200;
Bollinger;
Donchian;
RSI 30/70;
ADX/25;
MFI 20/80;
eventi FX effettivamente presenti.
13.5 Confronto con le baseline

Confronta almeno con:

Baseline bucket corrente
Compact:
90d=20, 180d=23, 365d=29

Standard:
90d=26, 180d=33, 365d=46

Full:
90d=35, 180d=49, 365d=75

Baseline Portfolio Full 1Y

Usa i valori reali del report precedente:

3 asset
60 istanze indicatore
75 bucket attuali per indicatore
4.500 righe indicatore
1.615 eventi
2.676.781 caratteri
circa 669.196 token


Misura il nuovo risultato reale dopo:

classi temporali;
selezione eventi;
entrambe le modifiche.

Non usare soltanto una stima lineare.

14. Report finale

Crea un nuovo report senza sovrascrivere i precedenti.

Percorso suggerito:

LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
report-phase00AiExportSignalDensityV2.md


Il report deve contenere:

executive summary;
modifiche implementate;
file e simboli modificati;
formula effettivamente implementata;
confronto formula teorica/runtime;
matrice delle 18 combinazioni;
classificazione dei plugin;
eventuali ambiguità nella classificazione;
distribuzione temporale dei bucket;
prima data non giornaliera per classe/detail;
raggiungimento progressivo dei delta;
confronto con i bucket attuali;
peso per indicatore;
peso per classe;
peso degli indicatori multi-output;
comportamento della selezione eventi;
eventi rilevati/esportati per annotation key;
confronto dimensionale prima/dopo;
risultati 3M/6M/1Y;
risultati Compact/Standard/Full;
conseguenze informative osservabili;
anomalie;
classificazioni da rivalutare;
parametri candidati per un eventuale fine tuning;
problemi P1 ancora aperti;
test e comandi eseguiti.
Parametri alternativi

Non applicare autonomamente parametri alternativi.

Nel report puoi proporre, per ciascuna classe, al massimo due configurazioni alternative se i probe mostrano problemi concreti, indicando:

motivo;
nuovi P/M/K;
conteggi;
differenza percentuale;
impatto token;
fascia temporale modificata.

La configurazione ufficiale deve restare quella indicata in questa specifica fino a nuova decisione.

15. Aggiornamento del manifest

Aggiungi al manifest diagnostico le informazioni necessarie a comprendere la rappresentazione:

technical_sampling:
  price_policy:
    detail_level: ...
    p: ...
    m: ...
    k: ...

  indicator_policies:
    - signal_instance_id: ...
      temporal_class: ...
      detail_level: ...
      p: ...
      m: ...
      k: ...
      bucket_count: ...


Per gli eventi:

event_selection:
  minimum_latest_events_per_annotation: 20
  complete_recent_window_days: 30
  grouped_by:
    - entity_id
    - annotation_key


Evita di ripetere inutilmente la stessa policy per ogni riga del payload. Se possibile, dichiara le policy una volta nel manifest e usa riferimenti stabili.

16. Compatibilità e versioning

Valuta e applica gli incrementi di versione necessari per:

schema snapshot;
dataset profile;
sampling policy;
event selection policy;
manifest;
eventuali response contract.

La modifica cambia la rappresentazione temporale e la completezza della lista eventi. Deve quindi essere auditabile.

Non mantenere un fallback silenzioso alla vecchia policy.

Se serve compatibilità di lettura:

rendila esplicita;
coprila con test;
documentala;
evita di produrre due payload differenti con la stessa versione dichiarata.
17. Vincoli finali
Non segmentare l’export.
Non troncare in base ai token.
Non modificare automaticamente il detail scelto.
Non eliminare asset o indicatori per ragioni dimensionali.
Non rilevare eventi sui bucket.
Non introdurre un relevance score.
Non applicare un cap di 20 agli eventi recenti.
Non distribuire artificialmente gli eventi storici.
Non reintrodurre Drawdown Recovery.
Non modificare la policy dei prezzi.
Non cambiare la formula.
Non scegliere parametri alternativi senza riportarli prima nel report.
18. Consegna

Al termine restituisci:

sintesi delle modifiche;
elenco dei file principali modificati;
percorso della documentazione aggiornata;
percorso del nuovo report;
percorso del probe JSON;
conteggi runtime delle 18 combinazioni;
eventuali differenze rispetto ai conteggi teorici;
dimensione Portfolio Full 1Y prima e dopo;
riduzione dovuta ai bucket;
riduzione dovuta agli eventi;
riduzione combinata;
annotation key maggiormente compresse;
indicatori che pesano maggiormente dopo la modifica;
classificazioni che richiedono ulteriore decisione;
test eseguiti con relativo esito;
problemi lasciati intenzionalmente aperti.
