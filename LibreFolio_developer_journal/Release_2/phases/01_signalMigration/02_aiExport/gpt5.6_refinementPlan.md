# Attività: rifattorizzazione AI Export, sampling temporale e documentazione tecnica

→ Piano applicativo:
[Phase 0 — AI Export dataset/analysis refinement](./plan-phase00AiExportRefinementImplementation.prompt.md)

Analizza lo stato corrente del sistema AI Export usando il codice come source of truth, quindi implementa il disegno descritto di seguito.

L’obiettivo è separare chiaramente:

1. i componenti dati granulari interni;
2. le fotografie dati composte e significative mostrate all’utente;
3. le richieste di analisi, formate da una o più fotografie più le istruzioni per l’LLM.

Aggiorna backend, frontend, profili, contratti e test in modo coerente. Non mantenere compatibilità architetturale artificiale con il disegno precedente se contrasta con quello nuovo; conserva invece le funzionalità utili migrandole nella nuova struttura.

---

## 1. Modello architetturale

Il nuovo modello deve essere:

```text
Componenti dati granulari interni
    → fotografie dati composte e versionate
    → esportazione data-only

Componenti dati granulari interni
    → fotografie richieste dall’analisi
    → istruzioni e response contract
    → prompt completo

Componenti granulari interni

Sotto il cofano i dati possono e devono essere divisi in componenti riutilizzabili, per esempio:

summary;
positions;
allocations;
performance;
contributions;
cash flows;
income;
fees;
taxes;
FIFO;
prices and returns;
FX;
technical indicators;
signals and events;
semantics e provenance necessarie.

Questi componenti non devono però diventare automaticamente voci autonome dell’interfaccia.

Fotografie mostrate all’utente

L’utente deve poter selezionare fotografie già composte, autosufficienti e dotate di un caso d’uso reale.

Non mostrare voci granulari prive di valore autonomo, come:

solo cash;
solo fee;
solo imposte;
attività e flussi isolati;
altri componenti tecnici interni.

La UI deve usare un menu a due livelli coerente con quello già adottato per i segnali:

Categoria
    → fotografia o analisi composta


Le fotografie disponibili devono dipendere dalla pagina e dal dominio.

Esempio concettuale per Dashboard:

Esporta dati
    → Panoramica portafoglio
    → Performance e flussi
    → Analisi tecnica del portafoglio
    → Lotti FIFO
    → Esportazione completa

Richiedi un’analisi
    → Piano di accumulo
    → Ribilanciamento
    → Attribuzione della performance
    → Analisi dei redditi
    → Revisione FIFO
    → Ampiezza tecnica
    → Descrizione del portafoglio


I nomi definitivi devono essere coerenti con la terminologia e la localizzazione esistenti.

Applicabilità per pagina

Filtra fotografie e analisi in base al contesto reale:

Dashboard: dati e analisi di portafoglio, inclusa FIFO;
Broker: dati e analisi limitati al broker, inclusa FIFO;
Asset: dati di identità, posizione, mercato, performance e tecnica; nessun export FIFO generale autonomo;
FX: dati del cambio, tecnica ed eventuali esposizioni dirette; nessun FIFO.

Una fotografia Asset relativa alla posizione può includere internamente un riepilogo o dettaglio dei lotti applicabili, se utile, ma non deve comparire una voce generale “FIFO Export” nella pagina Asset.

2. Catalogo delle fotografie e catalogo delle analisi

Crea due cataloghi logicamente distinti.

Catalogo delle fotografie dati

Ogni fotografia deve dichiarare:

identificatore stabile;
dominio;
versione;
pagine e scope applicabili;
componenti granulari richiesti;
dati obbligatori e opzionali;
requisiti tecnici;
regole di composizione;
semantica del periodo;
supporto ai livelli Compact, Standard e Full.

Prevedi anche una fotografia composta equivalente a:

All Applicable Data


Questa non deve essere un assembler monolitico duplicato. Deve concatenare ordinatamente tutte le fotografie o sezioni applicabili allo scope corrente, evitando duplicazioni.

Catalogo delle analisi

Ogni analisi deve dichiarare:

identificatore e versione;
fotografie o componenti richiesti;
dipendenze obbligatorie e opzionali;
istruzioni;
response contract;
supporto alle note;
eventuali condizioni di applicabilità.

Il task non deve più possedere necessariamente uno snapshot monolitico privato. Deve risolvere e comporre le fotografie necessarie.

Esempio concettuale:

analysis_profile:
  task: performance_attribution
  required_datasets:
    - portfolio_overview
    - performance_and_flows
    - income_fees_taxes
  optional_datasets:
    - market_context


Mantieni lookup deterministici, versioning esplicito e comportamento fail-closed in presenza di mismatch.

3. Periodo AI unico e autosufficiente

Elimina, nella UI AI Export, la distinzione tra periodo finanziario e finestra tecnica.

L’utente sceglie un solo periodo. Tale scelta definisce sempre:

dalla data iniziale risultante
fino a snapshot_as_of


Il periodo AI deve essere indipendente dal periodo selezionato nella Dashboard o nella pagina di provenienza.

Il testo copiato deve essere autosufficiente e non deve assumere che l’LLM:

conosca lo stato della pagina;
possa interrogare LibreFolio;
possa ottenere automaticamente altri dati;
conosca il periodo visualizzato altrove.

Il periodo unico deve applicarsi a tutti i dati temporali inclusi nella fotografia o nell’analisi:

performance;
contributi;
redditi;
fee e imposte;
prezzi e rendimenti;
FX;
indicatori;
segnali;
eventi;
altri dati periodici applicabili.
Warm-up

Gli indicatori possono richiedere dati precedenti all’inizio del periodo.

Il backend deve distinguere internamente:

calculation range
exported range


I dati precedenti devono essere usati soltanto per il warm-up e non devono comparire nell’export fuori dal periodo richiesto.

4. Significato di Compact, Standard e Full

I livelli non devono eliminare arbitrariamente entità finanziarie.

Rimuovi come meccanismo generale di compressione:

top-N delle posizioni;
top/bottom-N dei contributori;
limite arbitrario dei lotti;
troncamento degli eventi dovuto soltanto alla dimensione;
eliminazione automatica di sezioni per superamento di una stima token.

Come regola generale:

Compact, Standard e Full devono rappresentare lo stesso universo applicabile, variando soprattutto granularità temporale e dettaglio della rappresentazione.

In particolare:

tutti i contributori della performance devono essere esportati e ordinati;
tutte le posizioni applicabili devono restare presenti;
i lotti devono dipendere dalla fotografia scelta e dallo scope, non da un top-N implicito;
eventuali aggregazioni devono preservare il totale e la riconciliazione.

La differenza principale tra i livelli sarà la dimensione massima dei bucket temporali:

Compact  → massimo 30 giorni
Standard → massimo 14 giorni
Full     → massimo 7 giorni

5. Sampling temporale adattivo

Implementa una politica comune e deterministica basata sulla seguente funzione.

Siano:

x: distanza in giorni da snapshot_as_of;
P: parametro di forma;
M: punto di transizione;
K: dimensione massima asintotica del bucket, in giorni.

La funzione continua è:

f(x;P,M,K)=1+(K−1)max⁡(x−7,0)PMP+max⁡(x−7,0)Pf(x;P,M,K) = 1+(K-1) \frac{\max(x-7,0)^P} {M^P+\max(x-7,0)^P}

Il delta intero è:

D(x;P,M,K)=max⁡(1,round⁡(f(x;P,M,K)))D(x;P,M,K) = \max\left(1,\operatorname{round}(f(x;P,M,K))\right)

La costruzione dei confini deve essere iterativa:

x0=0x_0=0 xn+1=min⁡(T,xn+D(xn;P,M,K))x_{n+1} = \min\left(T,x_n+D(x_n;P,M,K)\right)

dove:

T è la durata totale del periodo richiesto in giorni;
ogni intervallo [xn,xn+1][x_n,x_{n+1}] genera un bucket;
l’ultimo bucket deve essere chiuso esattamente sulla data iniziale richiesta;
l’algoritmo deve terminare deterministicamente;
non devono esistere intervalli nulli o sovrapposti.
Parametri definitivi iniziali

Usa:

P = 2
M = 30


per tutti e tre i livelli.

Varia soltanto K:

Compact  → P=2, M=30, K=30
Standard → P=2, M=30, K=14
Full     → P=2, M=30, K=7


La scelta è intenzionale:

la forma e il punto di transizione restano comuni;
il livello controlla soltanto il massimo intervallo remoto;
Compact converge verso una rappresentazione mensile;
Standard converge verso una rappresentazione bisettimanale;
Full converge verso una rappresentazione settimanale.
Conteggi di riferimento

Con round, iterazione sui delta e chiusura dell’ultimo bucket esattamente a T, i conteggi attesi sono:

Compact:
- 90 giorni:  20 bucket
- 180 giorni: 23 bucket
- 365 giorni: 29 bucket

Standard:
- 90 giorni:  26 bucket
- 180 giorni: 33 bucket
- 365 giorni: 46 bucket

Full:
- 90 giorni:  35 bucket
- 180 giorni: 49 bucket
- 365 giorni: 75 bucket


Questi valori devono diventare test deterministici della policy.

Per Full, il delta arrotondato deve restare unitario per almeno le prime due settimane. Con i parametri scelti resta unitario fino a circa il sedicesimo giorno, quindi il vincolo è soddisfatto.

Test richiesti

Aggiungi test almeno per:

valori della funzione nei punti limite;
x <= 7 → delta uguale a 1;
monotonicità non decrescente del delta;
delta sempre compreso fra 1 e K;
convergenza verso K;
nessun bucket nullo;
nessun overlap;
copertura completa del periodo;
ultimo confine uguale a T;
conteggi a 90, 180 e 365 giorni;
comportamento su periodi inferiori a sette giorni;
comportamento su periodi Custom molto lunghi;
determinismo;
date non di mercato e osservazioni mancanti.
6. Bucket temporali

Non campionare semplicemente un singolo punto rappresentativo scartando ciò che accade tra due date.

Ogni intervallo determinato dalla formula deve diventare un bucket che preserva le informazioni economicamente rilevanti.

Prezzi e FX

Per ogni bucket conserva almeno, se disponibili:

start date
end date
first
maximum
minimum
last
observation count


La semantica è assimilabile a OHLC sulla serie giornaliera disponibile, senza implicare dati intraday.

Flussi

Per contributi, redditi, fee, imposte e altri eventi monetari aggregabili conserva:

start date
end date
total amount
event count

Performance

Mantieni informazioni compatibili con la semantica del Portfolio Engine, preservando almeno quanto necessario per comprendere:

valore iniziale e finale;
massimo e minimo;
rendimento del bucket;
P&L;
flussi esterni;
riconciliazione.

Non duplicare o reinventare calcoli già posseduti dagli engine finanziari.

Indicatori continui

Per indicatori numerici continui conserva, quando semanticamente valido:

first
minimum
maximum
last


Gestisci correttamente indicatori con output multipli.

Segnali ed eventi

Gli eventi discreti non devono essere mediati.

Il bucket comprime la serie numerica, ma deve conservare gli eventi materializzati e semanticamente distinti avvenuti nell’intervallo, salvo deduplicazione deterministica definita dal plugin.

Documenta chiaramente la differenza tra:

stato corrente;
serie continua;
transizione;
evento discreto.
7. Indicatori e Signal Plugin

AI Export non deve contenere conoscenza specifica duplicata su ogni indicatore o segnale.

Estendi il contratto comune degli indicatori e dei Signal Plugin affinché ciascun componente possa dichiarare o fornire concettualmente:

required_inputs()
minimum_history()
validate_input()
compute()
validate_output()
describe_for_ai()


Per i segnali, aggiungi anche la semantica degli eventi, per esempio:

describe_events_for_ai()


Adatta i nomi all’architettura reale del progetto, evitando astrazioni ridondanti.

Comportamento

La sequenza deve essere:

fotografia o analisi
    → richiede indicatore/segnale
    → risolve il plugin
    → verifica le capability della sorgente
    → valida gli input
    → calcola
    → valida l’output
    → applica i bucket
    → include dati e descrizione AI


Se un indicatore o segnale non è calcolabile:

omettilo;
non aggiungere placeholder;
non aggiungere nell’export una spiegazione della mancanza;
non bloccare gli altri indicatori disaccoppiati;
conserva il motivo soltanto nei meccanismi diagnostici interni, se opportuno.

Il prompt deve ricordare all’LLM:

Considerare disponibili soltanto i dati esplicitamente presenti e non inferire valori o disponibilità di indicatori, segnali o serie assenti.

Auto-discovery

Un nuovo plugin deve portare con sé:

requisiti;
validazione;
calcolo;
validazione dell’output;
descrizione AI;
semantica degli eventi.

Il plugin può comparire automaticamente nel catalogo dei segnali disponibili, ma non deve essere inserito silenziosamente in tutte le fotografie o analisi esistenti.

Quindi:

auto-discovery e auto-description: sì
inclusione automatica in ogni profilo: no

8. MFI, OBV e dati di volume

Per gli indicatori basati sul volume non basta verificare l’esistenza numerica della colonna.

Usa due livelli di validazione.

Validazione strutturale

Il plugin controlla deterministicamente:

colonne richieste;
numero minimo di osservazioni;
valori finiti;
volume non negativo;
presenza sufficiente di volumi non nulli;
date ordinate;
gestione dichiarata di buchi e duplicati;
output finale utilizzabile.
Validazione semantica

La sorgente o serie di mercato deve dichiarare una capability equivalente a:

supports_meaningful_volume


e, se utile:

volume_kind


MFI e OBV devono essere inclusi soltanto se:

capability semantica valida
AND
validate_input positivo
AND
validate_output positivo


Non basare questa decisione unicamente sull’asset type.

9. Prezzi, FX e dipendenze automatiche

Ogni fotografia o analisi deve poter richiedere automaticamente i dati necessari anche se provengono da un altro dominio tecnico.

Per esempio:

se un’analisi confronta valori in valute differenti
    → risolvi e includi automaticamente i cambi necessari

se un’analisi richiede un prezzo specifico
    → recupera il prezzo necessario anche dalla Dashboard

se un indicatore richiede warm-up
    → recupera internamente la serie precedente


Non costringere l’utente a conoscere queste dipendenze.

Mantieni esplicite le semantiche rilevanti:

serie usata dagli indicatori;
tipo di prezzo;
valuta;
data del prezzo;
cambio utilizzato;
direzione del cambio;
data del cambio;
conversione diretta, inversa o triangolata;
semantica di costo, valore, reddito e P&L.
10. Dimensione e stima token

La stima token deve essere soltanto informativa.

Non deve mai:

troncare dati;
rimuovere entità;
eliminare sezioni;
ridurre automaticamente il livello;
bloccare la copia;
modificare silenziosamente la composizione.

Se la stima è elevata, mostra un warning e suggerisci eventualmente un livello più compatto, mantenendo disponibile l’azione equivalente a:

Copia comunque


La riduzione di dimensione deve avvenire attraverso la policy Compact/Standard/Full e i relativi bucket, non tramite troncamento finale.

11. Guida agli export aggiuntivi

Aggiungi ai prompt di analisi una sezione generata dinamicamente che istruisca l’LLM a:

individuare chiaramente eventuali dati aggiuntivi necessari;
indicare all’utente quale fotografia LibreFolio esportare;
usare soltanto categorie e voci realmente disponibili nel contesto;
non assumere che dati LibreFolio non presenti nel prompt siano accessibili.

Esempio concettuale:

## Additional LibreFolio Data

If the available data is insufficient, identify the missing dataset and guide
the user to the corresponding LibreFolio AI Export entry.

Do not assume that LibreFolio data not included in this prompt is available.


L’elenco delle possibili voci deve essere generato dal catalogo reale e localizzato, non mantenuto manualmente nel template.

12. Calcoli dell’LLM

Aggiungi alle istruzioni condivise dei prompt di analisi la richiesta di usare una sandbox di calcolo quando disponibile.

La regola deve coprire:

calcoli;
aggregazioni;
confronti;
riconciliazioni;
simulazioni;
scenari;
aritmetica apparentemente semplice.

Richiedi inoltre:

verifica di unità, valute, segni e periodi;
controllo di coerenza indipendente;
dichiarazione delle ipotesi rilevanti;
indicazione se il risultato non è stato verificato programmaticamente perché la sandbox non era disponibile.

Non richiedere obbligatoriamente di stampare tutto il codice usato: interessa la correttezza verificabile del risultato.

13. Documentazione nella Developer Guide

Inaugura nella Developer Guide una nuova sezione dedicata agli aspetti tecnici di AI Export.

Non creare una singola pagina monolitica. Dividi la documentazione in più pagine, ciascuna con responsabilità chiara e dimensione ragionevole.

Organizzazione indicativa:

Developer Guide
└── AI Export
    ├── Overview and Architecture
    ├── Data Components and Composed Snapshots
    ├── Analysis Profiles and Prompt Composition
    ├── Time Range and Adaptive Sampling
    ├── Temporal Buckets and Aggregation Semantics
    ├── Technical Indicators and Signal Plugins
    ├── FX, Prices and Automatic Dependencies
    ├── Versioning, Validation and Failure Semantics
    ├── Frontend Integration and UX
    └── Testing and Extension Guide


Adatta titoli, percorso e indice al sistema documentale esistente.

Contenuti minimi
Overview and Architecture

Documenta:

modello mentale complessivo;
responsabilità backend/frontend;
separazione fra catalogo dati e catalogo analisi;
flusso completo fino alla clipboard;
confine privacy e assenza di chiamate LLM da LibreFolio.
Data Components and Composed Snapshots

Documenta:

granularità interna dei componenti;
motivazione della granularità;
perché i componenti interni non coincidono con le voci UI;
composizione delle fotografie;
applicabilità per dominio e pagina;
comportamento di All Applicable Data;
regole per evitare duplicazioni.
Analysis Profiles and Prompt Composition

Documenta:

dipendenze tra task e fotografie;
istruzioni condivise;
istruzioni specifiche;
response contract;
note utente;
lingua;
guida agli export aggiuntivi;
ordine esatto delle sezioni;
comportamento fail-closed.
Time Range and Adaptive Sampling

Documenta in dettaglio:

periodo AI unico;
indipendenza dal periodo della pagina;
differenza tra calculation range ed exported range;
warm-up;
funzione matematica;
significato di x, P, M, K e T;
discretizzazione mediante round;
costruzione iterativa dei confini;
chiusura dell’ultimo bucket;
parametri dei tre livelli;
conteggi attesi.

Includi la formula:

f(x;P,M,K)=1+(K−1)max⁡(x−7,0)PMP+max⁡(x−7,0)Pf(x;P,M,K) = 1+(K-1) \frac{\max(x-7,0)^P} {M^P+\max(x-7,0)^P}

e:

D(x;P,M,K)=max⁡(1,round⁡(f(x;P,M,K)))D(x;P,M,K) = \max\left(1,\operatorname{round}(f(x;P,M,K))\right)

con:

Compact  → P=2, M=30, K=30
Standard → P=2, M=30, K=14
Full     → P=2, M=30, K=7


Riporta i conteggi:

             90d   180d   365d
Compact       20     23      29
Standard      26     33      46
Full          35     49      75


Spiega perché sono state scartate come soluzione principale:

crescita lineare;
crescita quadratica o esponenziale non limitata;
sampling fisso “7 daily + 8 weekly”;
funzioni Weibull, logistica e Gompertz.

Non serve una trattazione estesa delle formule scartate: chiarisci che hanno comportamento operativo comparabile, ma maggiore complessità e minore leggibilità rispetto alla funzione razionale scelta.

Temporal Buckets

Documenta:

differenza tra point sampling e bucket;
preservazione di first/min/max/last;
somme dei flussi;
conteggio eventi;
indicatori multi-output;
segnali discreti;
riconciliazione;
trattamento di weekend, festività, buchi e date senza mercato.
Technical Indicators and Signal Plugins

Documenta:

contratto dei plugin;
requisiti;
warm-up;
validazione input/output;
descrizione AI;
auto-discovery;
regole di inclusione nei profili;
successo parziale;
MFI/OBV e capability semantica del volume.
Testing and Extension Guide

Documenta come un developer deve:

aggiungere un nuovo componente dati;
creare una fotografia composta;
associare fotografie a un’analisi;
aggiungere un nuovo indicatore;
aggiungere un Signal Plugin;
fornire la descrizione AI;
dichiarare capability e requisiti;
aggiungere test;
aggiornare versioni e contratti.
14. Test e verifica finale

Aggiorna o crea test backend e frontend coerenti con la nuova architettura.

Copri almeno:

cataloghi;
applicabilità per pagina;
composizione delle fotografie;
risoluzione delle dipendenze;
periodo unico;
warm-up escluso dall’output;
sampling e bucket;
conteggi deterministici;
aggregazioni;
indicatori omessi quando non validi;
capability volume;
descrizioni AI dei plugin;
FX recuperati automaticamente;
nessun troncamento;
warning dimensionale;
memoria UI;
clipboard;
localizzazione;
fail-closed su versioni o contratti incoerenti.

Esegui:

test unitari;
test di integrazione;
controlli statici;
build frontend;
test frontend esistenti e nuovi;
verifica manuale delle quattro pagine.

Verifica inoltre che la Developer Guide:

venga inclusa nella navigazione;
non abbia link rotti;
non duplichi documentazione esistente;
sia suddivisa realmente per argomento;
descriva il comportamento implementato, non soltanto il disegno teorico.
15. Consegna

Al termine:

riassumi l’architettura implementata;
elenca i file principali modificati;
descrivi eventuali migrazioni di profili o contratti;
riporta test, build e controlli eseguiti con relativo esito;
indica eventuali decisioni rimaste aperte;
segnala ogni divergenza motivata rispetto a questo disegno;
verifica esplicitamente che codice, test e Developer Guide siano coerenti tra loro.
