# <img src="../../../../../static/cssscraper.png" alt=""> CSS Scraper

Il provider CSS Scraper consente di estrarre i dati dei prezzi da qualsiasi pagina web utilizzando i selettori CSS. Questo è particolarmente utile per gli asset non coperti da altri provider, come i titoli di stato italiani (BTP) su Borsa Italiana.

## 📊 Capacità

- ✅ **Prezzo Attuale**: Estrae il prezzo da una pagina web
- ❌ **Storico**: Non supportato (⚠️ avviso, non un errore)
- ❌ **Ricerca**: Non supportata

## 🔧 Configurazione

- **Identifier**: L'URL completo della pagina da scansionare
- **Identifier Type**: `OTHER`
- **Parameters**:

| Parametro | Obbligatorio | Descrizione | Esempio |
|-----------|:---:|---|---|
| `current_css_selector` | ✅ | Selettore CSS per l'elemento del prezzo | `.summary-value strong` |
| `currency` | ✅ | Codice valuta ISO 4217 | `EUR` |
| `decimal_format` | ❌ | `us` (1,234.56) o `eu` (1.234,56) | `eu` |
| `timeout` | ❌ | Timeout HTTP in secondi (default: 30) | `30` |
| `user_agent` | ❌ | Header User-Agent personalizzato | `LibreFolio/1.0` |

## 🔎 Come Trovare il Selettore CSS

### Passaggi (Chrome)

1. Apri la pagina con il prezzo in Chrome
2. Fai **clic con il tasto destro** sul valore del prezzo
3. Seleziona **Ispeziona** (o premi `F12`)
4. Nel pannello Elementi dei DevTools, l'elemento del prezzo sarà evidenziato
5. Fai **clic con il tasto destro** sull'elemento evidenziato nei DevTools
6. Seleziona **Copia** → **Copia selettore**
7. Incollalo nel campo `current_css_selector`

### Passaggi (Firefox)

1. Apri la pagina con il prezzo in Firefox
2. Fai **clic con il tasto destro** sul valore del prezzo
3. Seleziona **Ispeziona elemento** (o premi `F12`)
4. Nell'Ispettore, fai **clic con il tasto destro** sull'elemento evidenziato
5. Seleziona **Copia** → **Selettore CSS**
6. Incollalo nel campo `current_css_selector`

### 💡 Esempio: Borsa Italiana BTP

Per un BTP su Borsa Italiana (es. `IT0005634800`):

**URL** (versione inglese):
```
https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en
```

**CSS Selector**:
```
.summary-value strong
```

**Configurazione**:
- Identifier: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
- `current_css_selector`: `.summary-value strong`
- `currency`: `EUR`
- `decimal_format`: `us` (la pagina inglese usa il formato US: 100.39)

Per la versione italiana, usa `decimal_format`: `eu` (la pagina italiana usa il formato EU: 100,39).

## 🔢 Formato Decimale

| Formato | Esempio | Quando usarlo |
|--------|---------|-------------|
| `us` | 1,234.56 | Pagine Inglesi/US (punto come separatore decimale) |
| `eu` | 1.234,56 | Pagine Italiane/Tedesche/Francesi (virgola come separatore decimale) |

## 🛠️ Risoluzione dei Problemi

### "Selector not found"
Il selettore CSS non corrisponde a nessun elemento nella pagina. La struttura della pagina potrebbe essere cambiata: ispeziona nuovamente e copia un nuovo selettore.

### "Connection timeout"
La pagina ha impiegato troppo tempo per rispondere. Prova ad aumentare il parametro `timeout` o verifica che l'URL sia corretto.

### "Parse error"
Non è stato possibile interpretare il testo del prezzo come numero. Controlla l'impostazione `decimal_format`: se la pagina mostra `100,39`, usa `eu`; se mostra `100.39`, usa `us`.

### Il prezzo mostra 0 o un valore errato
Il selettore potrebbe corrispondere a un elemento diverso. Prova un selettore più specifico. Usa i DevTools per verificare esattamente a quale elemento corrisponde il tuo selettore.
