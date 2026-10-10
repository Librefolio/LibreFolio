# 🇮🇹 Borsa Italiana

**Borsa Italiana** è la borsa valori di Milano, gestita da Euronext. Questo provider legge prezzi,
storico dei prezzi e dettagli degli strumenti dal suo sito web pubblico — non servono account né
chiave API.

## 🔍 Cosa Offre

- **Prezzo corrente**: l'ultimo prezzo di mercato. Per un fondo comune, il suo NAV — solo quando è
  datato oggi.
- **Storico**: apertura, massimo, minimo, chiusura e volume giornalieri. I fondi comuni non hanno
  serie storiche: ogni NAV viene salvato alla propria data, quindi lo storico cresce dal giorno in
  cui aggiungi il fondo.
- **Ricerca**: per nome o ISIN. Ogni strumento appare due volte, 🇮🇹 e 🇬🇧: la bandiera imposta la
  lingua del suo nome e della sua descrizione. Gli indici sono esclusi, poiché non puoi acquistarli.
  Nessun risultato? LibreFolio cerca anche una pagina Borsa Italiana corrispondente sul web, a meno
  che il tuo amministratore non abbia disattivato questa funzione.
- **Dettagli**: nome, tipo, valuta, un settore e una descrizione (mercato, emittente, scadenza,
  cedola); il ticker per le azioni; per i fondi, l'ISIN, le caratteristiche del fondo e i suoi costi.

Copre ciò che Borsa Italiana elenca — azioni italiane, ETF ed ETC (ETFplus), obbligazioni (MOT,
ExtraMOT, EuroTLX) e fondi chiusi (MIV) — oltre a fondi comuni e SICAV.

## 💱 Valuta e Tipo

- La **valuta** è quella in cui Borsa Italiana quota i prezzi: EUR per gli ETF e gli ETC su ETFplus,
  anche quando il fondo stesso è denominato in USD; USD per un'obbligazione negoziata in dollari su
  EuroTLX. Se LibreFolio non riesce a leggerla, lascia la tua valuta così com'è — controllala prima
  di salvare.
- **Tipo**: ETF, ETC ed ETN arrivano tutti come semplice **ETF**. Se sai cosa detiene il fondo,
  affinalo (ad esempio **Equity ETF** o **Commodity ETF**): un successivo
  [controllo rispetto ai dati del provider](../create-edit.md#provider-data-comparison) mantiene la
  tua scelta.
- Le **obbligazioni** ricevono il settore **Government Bonds** o **Corporate Bonds** (emittenti
  sovranazionali: **Financials**) e, quando l'emittente è riconosciuto, il suo paese — *United
  States of America* diventa **USA**.

## ✏️ Configuralo

**Ricerca Online** compila tutto. Per configurare il provider manualmente, apri l'asset con
**Modifica** (✏️) — o **+ Aggiungi Asset** per uno nuovo — ed espandi **Assegnazione Provider**:

1. Scegli **Borsa Italiana** come **Provider**.
2. Digita l'**ISIN** dello strumento, ad esempio `IT0003128367` (ENEL). Ogni pagina di strumento su
   [borsaitaliana.it](https://www.borsaitaliana.it) lo mostra.
3. Scegli la **Lingua**: 🇬🇧 English o 🇮🇹 Italiano.
4. Clicca **Test configurazione**, quindi salva.

**Ricerca Online** compila anche le altre tre impostazioni; impostale manualmente solo in questi
casi.

??? note "🧾 Codice interno del fondo — per un fondo comune o una SICAV"

    I fondi comuni sono prezzati tramite il codice fondo proprio di Borsa Italiana, non tramite
    l'ISIN. Trova il fondo su
    [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) e copia il codice
    dall'indirizzo della sua pagina: in `…/borsa/fondi/dettaglio/2FADB602822.html` il codice è
    `2FADB602822`. Lascia il campo vuoto per tutto il resto.

??? note "🧭 Market MIC e Platform — quando la pagina dello strumento non si apre"

    Alcuni mercati devono essere indicati esplicitamente. Apri lo strumento su borsaitaliana.it: il
    codice dopo l'ISIN nell'indirizzo della pagina è il **Market MIC** — in
    `…/scheda/US912810TU25-ETLX.html` è `ETLX`. **Platform** è necessario solo su EuroTLX, dove è
    `TLX`.

    | Mercato | Market MIC | Platform |
    |--------|:---:|:---:|
    | MTA (azioni italiane) | `MTAA` | — |
    | MOT (obbligazioni) | `MOTX` | — |
    | ExtraMOT (obbligazioni) | `XMOT` | — |
    | ETFplus (ETF, ETC) | `ETFP` | — |
    | MIV (fondi chiusi) | `MIVX` | — |
    | EuroTLX (obbligazioni) | `ETLX` | `TLX` |

    Ad esempio, l'obbligazione del Tesoro USA `US912810TU25` su EuroTLX funziona una volta che **Market MIC** è
    `ETLX` e **Platform** è `TLX`; i suoi prezzi sono in USD.

## 🧾 Fondi comuni e NAV

Il NAV di un fondo viene pubblicato una volta al giorno, con un ritardo. LibreFolio salva ogni NAV
alla data a cui si riferisce, mai come prezzo odierno: finché non arriva il successivo, il fondo è
valutato all'ultimo prezzo noto — quel NAV, o la tua operazione se è più recente.

Il codice del fondo è conservato sotto **Altri identificatori**; l'ISIN reale rimane
l'identificatore principale quando la pagina del fondo lo mostra.

## ⚠️ Limiti

- LibreFolio distanzia le sue richieste al sito web, quindi sincronizzare molti asset di Borsa
  Italiana può richiedere alcuni minuti.
- Un mercato che LibreFolio non riesce ancora a leggere restituisce un errore che ti chiede di
  segnalare l'ISIN su [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Correlati

- 📋 **[Panoramica Asset](../index.md)** — Gestisci la tua libreria di asset
- 🏦 **[Provider asset](./index.md)** — Altre fonti di dati
- 📡 **[justETF](./justetf.md)** — Fonte alternativa per i dati ETF
- 🛠️ **Per sviluppatori: [Borsa Italiana Provider](../../../developer/backend/assets/provider_borsa_italiana.md)** — Richieste, parsing delle pagine e mappatura dei campi
