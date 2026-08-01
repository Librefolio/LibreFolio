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



------

Sì, concordo: nel prompt finale P, M e K sono dettagli implementativi che non aiutano l’LLM a interpretare i dati. Manteniamo invece temporal_class e bucket_count, che descrivono sinteticamente velocità del segnale e densità effettivamente ricevuta.

# AI Export: alleggerimento manifest e probe replicabile dei prompt finali reali

Leggi integralmente:

- `report-phase00AiExportRuntimeDeepAudit.md`
- `report-phase00AiExportSizeAndTechnicalDensity.md`
- `report-phase00AiExportSignalDensityV2.md`
- `probe-phase00AiExportTechnicalDensity.json`
- `probe-phase00AiExportSignalDensityV2.json`
- la Developer Guide aggiornata dell’AI Export;
- il catalogo runtime di dataset e analisi;
- il renderer frontend realmente usato per produrre il testo copiabile;
- il runtime API dell’AI Export.

Questa attività ha tre obiettivi:

1. alleggerire il manifest pubblico rimuovendo i parametri implementativi del bucketing;
2. creare uno strumento stabile e replicabile che generi tutti i prompt finali reali disponibili;
3. misurare la dimensione dei prompt effettivamente copiabili, non del solo canonical JSON backend.

Non modificare ancora:

- formula di sampling;
- matrice interna `P/M/K`;
- classificazione temporale dei Signal Plugin;
- floor degli eventi;
- finestra recente degli eventi;
- formato delle tabelle indicatori;
- contenuto dei dataset;
- required/optional dataset delle analisi;
- response contract;
- catalogo pubblico.

Prima dobbiamo ottenere misure complete e realistiche sui prompt finali.

---

# 1. Rimozione di P, M e K dal manifest pubblico

I parametri:

```yaml
p: 2
m: 30
k: 7


sono dettagli implementativi della funzione di campionamento.

Sono utili:

nei test;
nei probe diagnostici;
nella Developer Guide;
nella configurazione interna;
nei report tecnici sul sampling.

Non sono invece utili nel prompt finale consegnato all’LLM e consumano caratteri ripetendosi per ogni policy.

Modifica richiesta

Rimuovi dal manifest pubblico renderizzato nel prompt:

p
m
k


per:

policy dei prezzi;
policy degli indicatori;
qualunque altra policy tecnica renderizzata all’interno del prompt.

Mantieni almeno:

technical_sampling:
  price_policy:
    detail_level: full
    bucket_count: 75

  indicator_policies:
    - signal_instance_id: ema_200
      signal_code: EMA
      temporal_class: very_slow
      detail_level: full
      bucket_count: 38


Valuta se detail_level debba essere ripetuto su ogni indicatore, dato che è già una proprietà globale della richiesta.

La preferenza è:

technical_sampling:
  detail_level: full

  price_policy:
    bucket_count: 75

  indicator_policies:
    - signal_instance_id: ema_200
      signal_code: EMA
      temporal_class: very_slow
      bucket_count: 38


Se tutti gli indicatori condividono il medesimo detail, evita di ripeterlo per ogni istanza.

Informazioni da conservare

Mantieni nel manifest pubblico:

detail_level, una volta sola se possibile;
signal_instance_id;
signal_code, se utile a interpretare l’istanza;
temporal_class;
bucket_count;
policy di selezione degli eventi;
ogni informazione necessaria a distinguere dati completi da dati campionati.

Mantieni nei probe diagnostici:

P;
M;
K;
classe;
conteggi teorici;
conteggi runtime;
confini temporali;
ampiezza dei bucket.

Quindi:

Prompt pubblico:
informazioni interpretative concise

Probe e documentazione:
dettagli matematici e implementativi completi

Test richiesti

Verifica che:

p, m e k non compaiano nel prompt renderizzato;
temporal_class e bucket_count continuino a comparire;
il detail sia presente almeno una volta;
i probe diagnostici continuino a contenere P/M/K;
i test della formula restino invariati;
il comportamento del sampling non cambi;
il manifest continui a essere sufficiente per capire che la storia è campionata;
schema e renderer restino coerenti.

Misura e riporta il risparmio effettivo del nuovo manifest nei prompt reali.

2. Oggetto corretto della misurazione

Il precedente probe misura soprattutto il canonical JSON del backend.

Per esempio:

portfolio.technical
Full
1Y


con circa 497.680 token-equivalenti rappresenta:

canonical JSON chars / 4


del dataset composto portfolio.technical.

Non rappresenta necessariamente:

una fotografia Export Data finale;
un prompt Request Analysis finale;
portfolio.all_data;
l’insieme di tutti i prompt;
il testo realmente copiato dall’utente.
Requisito fondamentale

Nel nuovo report deve essere scritto chiaramente:

La metrica decisionale principale è la dimensione del prompt finale realmente renderizzato e copiabile dall’utente. La dimensione del canonical JSON backend viene conservata soltanto come diagnostica per attribuire il peso ai dataset e ai componenti.

Per ogni prova conserva quindi due misure distinte:

canonical backend response
rendered final prompt


Le decisioni sul prodotto devono essere basate principalmente su:

rendered final prompt chars
rendered final prompt estimated token-equivalent

3. Database reale

Usa il database production locale del progetto.

Sono disponibili due utenti con dati reali fittizi e portfolio valorizzati:

username: alfy
password: Abc1234

username: marco
password: Abc1234


Si tratta di un ambiente production locale usato per report realistici, non di credenziali esposte verso un servizio pubblico.

Puoi usare direttamente queste credenziali per autenticarti mediante API.

Vincolo read-only

Il probe non deve modificare i dati applicativi.

Non eseguire:

import;
refresh dei prezzi;
bootstrap;
sincronizzazioni;
update;
migrazioni;
creazione o cancellazione di dati;
modifica delle preferenze;
salvataggio dei prompt nel database;
recompute persistenti.

La generazione dei prompt deve essere read-only.

Se il runtime effettua scritture automatiche, lavora su una copia del database production locale e documentalo.

Non inserire le password:

nei prompt salvati;
nei report;
nel JSON delle metriche;
nei nomi dei file;
nella documentazione;
nei log finali.
4. Script diagnostico permanente

Crea uno script stabile, versionato e rilanciabile con un solo comando.

Percorso suggerito:

backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py


Se il renderer ufficiale può essere eseguito correttamente soltanto tramite frontend/Node, puoi creare:

backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py
frontend/scripts/ai-export-render-prompt-probe.ts


Lo script Python deve restare l’orchestratore unico.

Il comando finale deve essere equivalente a:

pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py


Eventuali credenziali e opzioni possono essere:

valori predefiniti per questo ambiente locale;
variabili d’ambiente;
argomenti CLI.

Preferisci una configurazione chiara tramite CLI o variabili d’ambiente, ma il comando documentato deve permettere di eseguire l’intero audit senza modificare codice.

Proprietà richieste

Lo script deve essere:

deterministico;
idempotente;
auto-adattativo rispetto al catalogo runtime;
capace di autenticare entrambi gli utenti;
capace di interrogare l’API reale;
capace di scoprire dataset e analisi dal catalogo;
capace di genera­re i prompt tramite il renderer ufficiale;
capace di salvare i prompt su file;
capace di rileggerli e misurarli;
capace di produrre metriche machine-readable;
capace di produrre un sommario Markdown;
rilanciabile dopo modifiche future;
configurabile per eseguire tutto o un sottoinsieme.

Non duplicare manualmente nel probe:

catalogo;
required dataset;
optional dataset;
versioni;
applicabilità;
ordine delle sezioni;
template dei prompt.

Queste informazioni devono provenire dalle source of truth runtime.

5. Uso dell’API reale

Esegui il flusso end-to-end tramite API:

login
→ catalog discovery
→ selection discovery
→ request construction
→ AI Export API
→ official prompt renderer
→ file output
→ metrics extraction


Non chiamare soltanto direttamente i service backend, perché vogliamo verificare ciò che l’utente riceve effettivamente.

È accettabile chiamare internamente il service soltanto per produrre breakdown diagnostici aggiuntivi che l’API non espone. La misura primaria deve però derivare dal percorso API e dal renderer ufficiale.

Registra per ogni richiesta:

metodo;
route;
status HTTP;
durata;
selection ID;
selection kind;
version;
utente anonimizzato;
domain;
scope;
period;
detail;
hash della response;
hash del prompt renderizzato.

Non salvare:

password;
cookie;
bearer token;
header di autenticazione.
6. Cartella degli output

Salva tutti gli artefatti del probe sotto una cartella dedicata.

Percorso suggerito:

LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/real_prompt_probe/


La cartella deve contenere almeno:

prompts/
metrics.json
summary.md
run_manifest.json
failures.json

Prompt

Salva ogni prompt finale in un file testuale.

Usa l’estensione corrispondente al formato realmente generato:

.md
.yaml
.txt


Non salvare il canonical JSON come se fosse un prompt. Se serve conservarlo per diagnosi, usa una sottocartella separata:

canonical/

Nomi dei file

Il nome deve rendere immediatamente identificabile il caso.

Formato consigliato:

{user}__{mode}__{domain}__{selection_id}__{scope}__{period}__{detail}.{ext}


Esempi:

alfy__data__portfolio__portfolio.technical__all__1Y__full.md
alfy__data__portfolio__portfolio.all_data__all__6M__standard.md
marco__analysis__portfolio__portfolio.rebalancing__all__1Y__compact.md
marco__analysis__broker__broker.review__broker_3__3M__full.md
alfy__analysis__asset__asset.trend_analysis__asset_anon_01__1Y__full.md
alfy__data__fx__fx.market_technical__eur_usd__1Y__standard.md


Sanitizza gli ID per renderli validi nei nomi dei file.

Per gli asset e i broker puoi usare:

asset_anon_01
broker_anon_01


ma mantieni una mappa soltanto nel manifest locale del run, senza dati sensibili nel report pubblico.

Sovrascrittura

Ogni esecuzione deve:

creare una cartella identificata da timestamp oppure commit hash;
non confondere output di run differenti;
aggiornare facoltativamente un link o una cartella latest;
consentire il confronto con un run precedente.

Esempio:

real_prompt_probe/
  2026-07-30T194500Z/
    prompts/
    canonical/
    metrics.json
    summary.md
    run_manifest.json
    failures.json

7. Catalog discovery dinamico

Interroga dinamicamente il catalogo disponibile.

Devi scoprire:

tutti i dataset Export Data;
tutti gli all_data;
tutte le analisi Request Analysis;
domini;
versioni;
required datasets;
optional datasets;
parametri necessari;
applicabilità;
response contract;
eventuali capability flags.

Non codificare una lista statica di 18 dataset o 16 analisi.

Il probe deve continuare a funzionare quando il catalogo crescerà.

Se viene aggiunta una nuova analisi o un nuovo dataset, il successivo run deve rilevarlo e provarlo automaticamente, se applicabile.

8. Inventario degli utenti

Prima dei prompt, raccogli per ciascun utente:

broker count
position count
unique held asset count
historical asset count
priced asset count
technical eligible asset count
technical covered asset count
duplicate asset legs across brokers
currency count
FX pair count
earliest price date
latest price date
transaction count
FIFO lot count


Questi dati servono a interpretare la dimensione.

Non riportare nel report:

password;
token;
valori totali dei portafogli;
quantità detenute;
importi delle transazioni;
note personali.
9. Fotografie Export Data

Genera tutti i prompt finali disponibili nella modalità:

Export Data


Per ogni utente esegui tutte le fotografie applicabili scoperte dal catalogo.

Portfolio

Esegui almeno:

portfolio completo
ogni dataset selezionabile
all_data


Se la UI consente scope per broker, esegui anche:

ogni broker;
portfolio complessivo;
eventuali combinazioni pubblicamente rappresentabili.
Broker

Esegui ogni dataset Broker applicabile per ogni broker reale.

Asset

È sufficiente scegliere un solo asset per utente, purché abbia:

almeno un anno di prezzi;
prezzo corrente valido;
indicatori tecnici calcolabili;
applicabilità finanziaria sufficiente ai task Asset.

Se più asset soddisfano i requisiti, seleziona deterministicamente:

quello con la storia più lunga;
in caso di parità, quello con più osservazioni;
in caso di ulteriore parità, ID crescente.

Registra nel manifest:

selection_reason: longest_history_at_least_1y
history_start
history_end
observation_count
technical_indicator_count


Anonimizza l’asset nel nome file e nel report.

FX

È sufficiente una sola coppia per utente, purché:

sia applicabile al portafoglio;
abbia almeno un anno di storia;
abbia rate validi;
consenta gli indicatori FX.

Se più coppie sono idonee, seleziona deterministicamente quella con:

storia più lunga;
numero maggiore di osservazioni;
chiave canonica crescente.

Se il noto coupling FX produce 503, registra il fallimento e continua il resto del probe.

10. Task Request Analysis

Genera tutti i prompt finali disponibili nella modalità:

Request Analysis


Per ciascun utente:

scopri tutte le analisi dal catalogo;
valuta l’applicabilità;
costruisci tutti i task applicabili;
usa gli scope reali;
renderizza il prompt finale;
salvalo nella cartella;
misura il file salvato.
Scope
Portfolio

Esegui sul portfolio completo.

Se l’analisi supporta scope broker, eseguila anche sui broker reali applicabili.

Broker

Esegui per ogni broker reale applicabile.

Asset

Usa l’unico asset selezionato secondo i criteri precedenti.

FX

Usa l’unica coppia FX selezionata secondo i criteri precedenti.

Non creare combinazioni non supportate dalla UI o dal catalogo.

11. Matrice dei parametri

Per ogni fotografia e task applicabile esegui:

Period:
- 3M
- 6M
- 1Y

Detail:
- Compact
- Standard
- Full


Quindi ogni prompt applicabile deve essere provato su nove combinazioni:

3 periodi × 3 detail

Custom

Aggiungi un caso Custom separato se:

il prompt supporta Custom;
esiste storia precedente a un anno;
il runtime consente di costruire un intervallo valido.

Usa:

start = prima data effettivamente utilizzabile
end = snapshot_as_of


Non mescolare Custom nelle medie della matrice principale.

Applicabilità temporale

Se un asset o una coppia possiede meno dati del periodo richiesto:

non simulare dati;
registra il periodo richiesto;
registra il periodo effettivo;
indica se il prompt è riuscito;
non selezionare come asset/FX principale un caso con meno di un anno se esiste un’alternativa idonea.
12. Misurazione del file reale

Dopo aver salvato ogni prompt:

rileggi il file dal filesystem;
misura:
caratteri Unicode;
byte UTF-8;
numero righe;
numero parole, eventualmente diagnostico;
hash SHA-256;
verifica che la misura coincida con la stringa prodotta dal renderer;
usa il contenuto del file per la stima token.

La misura decisionale è quindi:

prompt_file_content


non:

response JSON object

13. Token estimation del prompt finale

Per ogni file prompt calcola obbligatoriamente:

chars_div_4_v1


e chiamalo:

estimated_token_equivalent_chars_div_4


Questa metrica serve per continuità con i probe precedenti.

Se è già disponibile localmente un tokenizer compatibile con il modello target, aggiungi:

tokenizer_name
tokenizer_version
token_count


Non installare una dipendenza production e non richiedere Internet.

Se non è disponibile un tokenizer adeguato, non inventare token esatti.

Nel report usa formulazioni come:

circa 120.000 token-equivalenti secondo chars/4


e non:

il prompt ha esattamente 120.000 token

14. Breakdown del prompt finale

Per ogni prompt misura separatamente, quando presenti:

Analysis Objective
Shared Verification Instructions
Response Contract
Snapshot Metadata and Dataset Manifest
Snapshot Data
Additional LibreFolio Data
Domain Notes
User Notes
Response Language


All’interno di Snapshot Data, attribuisci il peso a:

dataset
component
technical prices
technical indicators
technical events
technical breadth
financial overview
holdings/allocation
performance/flows
transactions
FIFO/lots
costs/taxes
FX
other


Il breakdown deve riconciliarsi con il numero di caratteri del file:

sum(attributed sections)
+ explicitly measured separators/wrappers
= file characters


Non accettare breakdown che non riconciliano.

15. Distinzione nel report

Il report deve separare esplicitamente:

Component density

Quanto pesano i mattoncini interni.

Dataset density

Quanto pesa il canonical backend response di ogni dataset composto.

Data snapshot prompt density

Quanto pesa il prompt finale di ogni fotografia Export Data.

Analysis task prompt density

Quanto pesa il prompt finale di ogni Request Analysis.

La tabella principale per le decisioni deve usare:

rendered prompt estimated token-equivalent


La dimensione del canonical JSON deve comparire come informazione diagnostica secondaria.

16. Metriche per ogni prompt

Per ogni prompt salva in metrics.json almeno:

run_id: ...
user_alias: alfy
mode: data | analysis
domain: portfolio | broker | asset | fx
selection_id: ...
selection_kind: dataset | analysis
selection_version: ...
scope_id: ...
period_label: 1Y
period_start: ...
period_end: ...
effective_period_start: ...
effective_period_end: ...
detail_level: full

status: ok | failed | skipped
failure_code: ...
failure_message_sanitized: ...

required_datasets: [...]
optional_datasets_declared: [...]
optional_datasets_included: [...]
optional_datasets_omitted: [...]
components_included: [...]

canonical_backend_chars: ...
canonical_backend_bytes: ...
canonical_backend_estimated_token_equivalent: ...

prompt_file: ...
rendered_prompt_chars: ...
rendered_prompt_bytes: ...
rendered_prompt_lines: ...
rendered_prompt_sha256: ...
rendered_prompt_estimated_token_equivalent: ...

section_breakdown: ...
dataset_breakdown: ...
component_breakdown: ...

17. Lettura diagnostica dei prompt

Lo script deve poter rileggere i prompt salvati per:

ricontrollare le dimensioni;
estrarre le intestazioni;
verificare la presenza delle sezioni;
verificare che P/M/K non siano presenti;
verificare che temporal_class e bucket_count siano presenti quando applicabili;
verificare che required e optional corrispondano al manifest;
controllare eventuali duplicazioni grossolane;
verificare che non siano presenti segreti.

Non serve inserire il contenuto completo dei prompt nel report.

Il report può citare:

struttura;
intestazioni;
dimensioni;
conteggi;
hash;
anomalie.
18. Controllo dei segreti

Aggiungi una scansione automatica dei file generati per cercare almeno:

Abc1234
Authorization:
Bearer 
access_token
refresh_token
cookie
set-cookie
password


Gestisci i falsi positivi derivanti da parole descrittive come password, ma fallisci esplicitamente se compare il valore reale della password o un token.

Il probe deve fallire se un segreto reale compare in:

prompt;
metrics;
summary;
manifest;
failure log.
19. Report richiesto

Crea:

LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
report-phase00AiExportRealPromptDensity.md


Il report deve dichiarare nelle prime righe:

Questo report misura principalmente la dimensione dei prompt finali renderizzati e copiabili dall’utente. Le misure del canonical JSON backend sono riportate soltanto per attribuire il peso a dataset e componenti.

Il report deve contenere:

executive summary;
oggetto corretto della misura;
differenza tra componente, dataset, fotografia e task;
ambiente e database;
verifica read-only;
inventario anonimizzato di alfy e marco;
catalogo scoperto dinamicamente;
numero totale di fotografie generate;
numero totale di task generati;
matrice 3M/6M/1Y × Compact/Standard/Full;
caso Custom;
risultati Portfolio;
risultati Broker;
risultati Asset;
risultati FX;
canonical JSON contro prompt renderizzato;
breakdown delle sezioni dei prompt;
breakdown per dataset;
breakdown per componente;
impatto della rimozione P/M/K;
manifest pubblico risultante;
fotografie più pesanti;
task più pesanti;
distribuzione min/mediana/P75/P90/max;
confronto alfy/marco;
scalabilità rispetto al numero di asset;
prompt falliti o saltati;
omissioni optional;
anomalie di composizione;
test e validazioni;
decisioni ancora da prendere.
20. Tabelle obbligatorie nel report
Fotografie Export Data
User
Domain
Dataset
Scope
Period
Detail
Rendered chars
Estimated token-equivalent
Largest section
Status

Task Request Analysis
User
Domain
Analysis
Scope
Period
Detail
Rendered chars
Estimated token-equivalent
Required datasets
Optional included
Technical share
Status

Distribuzione per tipo
Output type
Count
Minimum
Median
P75
P90
Maximum

Casi massimi
Rank
User
Mode
Domain
Selection
Scope
Period
Detail
Estimated token-equivalent

Canonical contro rendered
Selection
Canonical backend chars
Rendered prompt chars
Difference
Rendered/canonical ratio

Impatto manifest
Prompt
Manifest before
Manifest after removal of P/M/K
Saved chars
Saved token-equivalent

21. Sommario automatico del run

Oltre al report principale, lo script deve produrre automaticamente:

summary.md


all’interno della cartella del run.

Il sommario deve essere generato direttamente dalle metriche e contenere:

timestamp;
commit;
ambiente;
utenti riusciti;
catalogo scoperto;
prompt previsti;
prompt generati;
prompt falliti;
totale caratteri;
fotografia più pesante;
task più pesante;
mediana fotografie;
mediana task;
fallimenti FX;
esito secret scan;
esito read-only verification.

Il report di Developer Journal può poi analizzare più estesamente lo stesso metrics.json.

22. Modalità dello script

Supporta almeno:

# Audit completo
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py

# Solo un utente
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --user alfy

# Solo fotografie
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --mode data

# Solo task
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --mode analysis

# Solo un dominio
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --domain portfolio

# Solo una combinazione
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --period 1Y \
  --detail full


Aggiungi:

--output-dir
--base-url
--keep-canonical
--compare-with
--fail-on-regression


se coerenti con l’architettura esistente.

23. Confronto tra run

Predisponi lo script affinché in futuro possa confrontare due esecuzioni:

pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py \
  --compare-with path/to/previous/metrics.json


Il confronto deve produrre per ogni prompt stabile:

previous chars
current chars
absolute delta
percentage delta
status change
dataset change
component change


La chiave stabile di confronto deve essere composta almeno da:

user alias
mode
domain
selection ID
scope
period
detail


Il confronto non deve fallire soltanto perché il catalogo contiene un nuovo prompt. Deve segnalarlo come:

added
removed
changed
unchanged
failed
recovered

24. Test automatici

Aggiungi test mirati per:

catalog discovery dinamico;
naming dei file;
sanitizzazione dei nomi;
scelta deterministica dell’asset;
scelta deterministica della coppia FX;
matrice period/detail;
salvataggio e rilettura dei prompt;
conteggio caratteri;
conteggio byte;
hash;
breakdown riconciliato;
assenza di P/M/K nel prompt;
presenza di temporal_class;
presenza di bucket_count;
secret scan;
prompt deterministico;
confronto tra run;
gestione dei fallimenti HTTP;
prosecuzione dopo failure FX;
nessuna scrittura sul DB.
25. Artefatti finali

Al termine devono esistere:

backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py


ed eventuale entrypoint frontend necessario:

frontend/scripts/ai-export-render-prompt-probe.ts


Inoltre:

real_prompt_probe/<run_id>/prompts/
real_prompt_probe/<run_id>/canonical/
real_prompt_probe/<run_id>/metrics.json
real_prompt_probe/<run_id>/summary.md
real_prompt_probe/<run_id>/run_manifest.json
real_prompt_probe/<run_id>/failures.json


e il report:

report-phase00AiExportRealPromptDensity.md

26. Consegna finale

Al termine restituisci:

sintesi delle modifiche;
file modificati;
comando unico per rilanciare il probe;
percorso dello script;
percorso della cartella del run;
percorso del report;
numero di dataset scoperti;
numero di analisi scoperte;
numero di fotografie generate;
numero di task generati;
numero di prompt falliti;
fotografia più pesante;
task più pesante;
mediana delle fotografie;
mediana dei task;
differenza tra canonical JSON e prompt renderizzato;
risparmio ottenuto rimuovendo P/M/K;
asset selezionato per utente e criterio, in forma anonimizzata;
coppia FX selezionata e criterio;
esito dei probe FX;
conferma che le metriche principali riguardano i prompt finali;
esito del controllo read-only;
esito della secret scan;
test eseguiti e risultati;
problemi ancora aperti.

Non applicare ulteriori politiche di compressione prima della revisione di questo report.
