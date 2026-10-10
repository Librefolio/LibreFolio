# <img src="../../../../static/cssscraper.png" alt=""> CSS Scraper

Il CSS Scraper legge il prezzo di un asset da qualsiasi pagina web pubblica, usando un selettore CSS che punta
al numero. Usalo quando nessun altro provider copre lo strumento. Nell'elenco **Provider** è
chiamato **CSS Web Scraper**.

## 🔍 Cosa offre

- ✅ **Prezzo corrente**: letto dalla pagina a ogni sincronizzazione, nella valuta che scegli.
- ❌ **Storico**: nessuno. Ogni sincronizzazione salva il prezzo del giorno, quindi lo storico cresce dal giorno in cui
  inizi.
- ❌ **Ricerca** e **dettagli**: assenti — inserisci tu stesso l'indirizzo della pagina e le impostazioni.

## 🧩 Configuralo

### 1️⃣ Copia il selettore CSS del prezzo

Il selettore indica a LibreFolio quale elemento della pagina contiene il prezzo.

=== "Chrome"

    1. Apri la pagina e fai clic con il pulsante destro sul prezzo.
    2. Scegli **Ispeziona** (o premi `F12`): DevTools evidenzia l'elemento del prezzo.
    3. Fai clic con il pulsante destro sull'elemento evidenziato, poi **Copia** → **Copia selettore**.

=== "Firefox"

    1. Apri la pagina e fai clic con il pulsante destro sul prezzo.
    2. Scegli **Ispeziona** (o premi `F12`): l'Ispettore evidenzia l'elemento del prezzo.
    3. Fai clic con il pulsante destro sull'elemento evidenziato, poi **Copia** → **Selettore CSS**.

### 2️⃣ Compila le impostazioni del provider

In **Assegnazione provider**, scegli **CSS Web Scraper** e incolla l'indirizzo della pagina in **URL**. Le
impostazioni appaiono con i loro nomi tecnici:

| Impostazione | Obbligatorio | Cosa inserire |
|---|:---:|---|
| `current_css_selector` | ✅ | Il selettore che hai copiato, ad es. `.summary-value strong` |
| `currency` | ✅ | La valuta del prezzo, ad es. `EUR` |
| `decimal_format` | — | `us` per `1,234.56` (predefinito) oppure `eu` per `1.234,56` |
| `timeout` | — | Secondi di attesa per la pagina (predefinito `30`) |
| `user_agent` | — | Come LibreFolio si presenta al sito (predefinito `LibreFolio/1.0`) |

### 3️⃣ Provalo

Fai clic su **Test configurazione**: **Prezzo corrente** deve mostrare il numero che vedi sulla pagina. Il ⚠️ su
**Storico** è previsto, poiché questo provider non ne ha.

!!! example "Un BTP su Borsa Italiana"

    - **URL**: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
    - `current_css_selector`: `.summary-value strong`
    - `currency`: `EUR`
    - `decimal_format`: `us` — la pagina inglese mostra `100.39`. La pagina italiana (`lang=it`)
      mostra `100,39`, quindi lì usa `eu`.

    Per gli strumenti quotati su Borsa Italiana, anche il provider [Borsa Italiana](borsa-italiana.md) ne fornisce lo storico.

## 🛠️ Risoluzione dei problemi

| Cosa vedi | Cosa fare |
|---|---|
| **Elemento del prezzo non trovato** | Il layout della pagina potrebbe essere cambiato: copia di nuovo il selettore. |
| **Impossibile interpretare il prezzo** | Controlla `decimal_format`. L'elemento deve contenere solo il numero: gli spazi, €, $, £, ¥ e % vengono ignorati, mentre i caratteri alfabetici come `EUR` non vengono ignorati. |
| **Errore HTTP** o **Richiesta non riuscita** | Controlla l'URL; aumenta `timeout` per un sito lento. L'errore 403 significa che il sito rifiuta le visite automatizzate. |
| Un numero errato | Il selettore corrisponde a un altro elemento (LibreFolio usa la prima corrispondenza): rendilo più specifico. |

## ⚠️ Limiti

- LibreFolio legge la pagina così come il sito la invia, senza eseguirne gli script: un prezzo inserito
  da JavaScript non può essere letto, né possono esserlo le pagine dietro un login.
- Quando il sito cambia layout, il selettore potrebbe smettere di corrispondere: prova di nuovo e copia un nuovo selettore.

## 🔗 Correlati

- ✏️ **[Editor dati](../detail/data-editor.md)** — Inserisci o correggi i prezzi manualmente
- 🛠️ **Per gli sviluppatori: [Provider CSS Scraper](../../../developer/backend/assets/provider_cssscraper.md)** — Richiesta, analisi e codici di errore
