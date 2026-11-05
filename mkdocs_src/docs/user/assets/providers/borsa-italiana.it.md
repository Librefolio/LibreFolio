# 🇮🇹 Borsa Italiana

**Borsa Italiana** è la borsa valori di Milano, gestita da Euronext. Questo provider legge i prezzi, lo storico dei prezzi e i dettagli degli strumenti dal suo sito web pubblico — non servono account né chiavi API.

## 🔍 Cosa offre

- **Prezzo corrente**: l'ultimo prezzo di mercato. Per un fondo comune, il suo NAV — solo quando è datato oggi.
- **Storico**: apertura, massimo, minimo, chiusura e volume giornalieri. I fondi comuni non hanno serie storiche: ogni NAV viene salvato alla propria data, quindi lo storico cresce dal giorno in cui aggiungi il fondo.
- **Ricerca**: per nome o ISIN. Ogni strumento compare due volte, 🇮🇹 e 🇬🇧 — oppure solo nella tua [lingua preferita](#preferred-language): la bandiera imposta la lingua del suo nome e della descrizione. Gli indici sono esclusi, poiché non puoi acquistarli. Nessun risultato? LibreFolio cerca anche una pagina corrispondente di Borsa Italiana sul web, a meno che il tuo amministratore non abbia disattivato questa opzione.
- **Dettagli**: nome, tipo, valuta, un settore e una descrizione (mercato, emittente, scadenza, cedola); il ticker per le azioni; per i fondi, l'ISIN, le caratteristiche del fondo e i suoi costi.

Copre ciò che Borsa Italiana quota — azioni italiane, ETF ed ETC (ETFplus), obbligazioni (MOT, ExtraMOT, EuroTLX) e fondi chiusi (MIV) — oltre a fondi comuni e SICAV.

## 💱 Valuta e tipo

- **Valuta** è quella in cui Borsa Italiana quota i prezzi: EUR per gli ETF e gli ETC su ETFplus, anche quando il fondo stesso è denominato in USD; USD per un'obbligazione scambiata in dollari su EuroTLX. Se LibreFolio non riesce a leggerla, lascia la tua valuta così com'è — controllala prima di salvare.
- **Tipo**: ETF, ETC ed ETN arrivano tutti come semplice **ETF**. Se sai cosa detiene il fondo, affinalo (ad esempio **ETF azionario** o **ETF su materie prime**): un successivo [controllo rispetto ai dati del provider](../create-edit.md#provider-data-comparison) mantiene la tua scelta.
- Le **obbligazioni** ricevono il settore **Obbligazioni governative** o **Obbligazioni societarie** (emittenti sovranazionali: **Finanziari**) e, quando l'emittente è riconosciuto, il suo paese — *Stati Uniti d'America* diventano **USA**.

## ✏️ Configuralo

**Cerca online** compila tutto. Per configurare il provider manualmente, apri l'asset con **Modifica** (✏️) — oppure **+ Aggiungi asset** per uno nuovo — ed espandi **Assegnazione provider**:

1. Scegli **Borsa Italiana** come **Provider**.
2. Digita l'**ISIN** dello strumento, ad esempio `IT0003128367` (ENEL). Ogni pagina dello strumento su [borsaitaliana.it](https://www.borsaitaliana.it) lo mostra.
3. Scegli la **Lingua**: 🇬🇧 Inglese o 🇮🇹 Italiano.
4. Clicca su **Verifica configurazione**, quindi salva.

**Cerca online** compila anche le altre tre impostazioni; impostale manualmente solo in questi casi.

??? note "🧾 Codice interno del fondo — per un fondo comune o una SICAV"

    Il prezzo dei fondi comuni viene recuperato tramite il codice fondo proprio di Borsa Italiana, non tramite l'ISIN. Trova il fondo su [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) e copia il codice dall'indirizzo della sua pagina: in `…/borsa/fondi/dettaglio/2FADB602822.html` il codice è `2FADB602822`. Per tutti gli altri strumenti, lascia il campo vuoto.

??? note "🧭 MIC del mercato e Piattaforma — quando la pagina dello strumento non si apre"

    Alcuni mercati devono essere specificati esplicitamente. Apri lo strumento su borsaitaliana.it: il codice dopo l'ISIN nell'indirizzo della pagina è il **MIC del mercato** — in `…/scheda/US912810TU25-ETLX.html` è `ETLX`. La **Piattaforma** è necessaria solo su EuroTLX, dove è `TLX`.

    | Mercato | MIC del mercato | Piattaforma |
    |--------|:---:|:---:|
    | MTA (azioni italiane) | `MTAA` | — |
    | MOT (obbligazioni) | `MOTX` | — |
    | ExtraMOT (obbligazioni) | `XMOT` | — |
    | ETFplus (ETF, ETC) | `ETFP` | — |
    | MIV (fondi chiusi) | `MIVX` | — |
    | EuroTLX (obbligazioni) | `ETLX` | `TLX` |

    Ad esempio, l'obbligazione del Tesoro USA `US912810TU25` su EuroTLX funziona una volta che il **MIC del mercato** è `ETLX` e la **Piattaforma** è `TLX`; i suoi prezzi sono in USD.

### 🌐 La tua lingua preferita {: #preferred-language }

Scegli sempre la stessa lingua nella ricerca? Impostala una volta come **Lingua preferita**, sotto **Borsa Italiana** in **Impostazioni › Plugin**, oppure con **Configura** accanto al provider nella finestra di dialogo dell'asset. Le tue ricerche mostreranno quindi ogni strumento una volta sola, 🇮🇹 Italiano o 🇬🇧 Inglese. L'impostazione **Entrambe le lingue**, quella predefinita, mostra entrambe, prima l'italiano. Il sito web viene cercato allo stesso modo qualunque sia la tua scelta.

È un'impostazione personale: cambia solo le tue ricerche, mai un prezzo o un asset che possiedi già, e la **Lingua** di un asset configurato manualmente resta a tua scelta. Vedi [Impostazioni dei plugin](../../settings/plugins.md#search-preferences).

## 🧾 Fondi comuni e NAV

Il NAV di un fondo viene pubblicato una volta al giorno, con un ritardo. LibreFolio salva ogni NAV alla data a cui si riferisce, mai come prezzo di oggi: finché non arriva il successivo, il fondo è valutato all'ultimo prezzo noto — quel NAV, o la tua operazione se è più recente.

Il codice del fondo è conservato sotto **Altri identificatori**; l'ISIN reale resta l'identificatore principale quando la pagina del fondo lo mostra.

## ⚠️ Limiti

- LibreFolio distanzia le richieste al sito web, quindi sincronizzare molti asset di Borsa Italiana può richiedere alcuni minuti.
- Un mercato che LibreFolio non riesce ancora a leggere restituisce un errore che ti chiede di segnalare l'ISIN su [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Correlati

- 📋 **[Panoramica degli asset](../index.md)** — Gestisci la tua libreria di asset
- 🏦 **[Provider asset](./index.md)** — Altre fonti di dati
- 📡 **[justETF](./justetf.md)** — Fonte alternativa per i dati degli ETF
- 🧩 **[Impostazioni dei plugin](../../settings/plugins.md)** — La tua lingua preferita nella ricerca
- 🛠️ **Per gli sviluppatori: [Provider Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)** — Richieste, analisi delle pagine e mappatura dei campi
