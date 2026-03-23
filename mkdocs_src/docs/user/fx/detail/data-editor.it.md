# ✏️ Editor dei dati e importazione CSV

L'Editor dei dati ti permette di **visualizzare, aggiungere, modificare e eliminare** i singoli punti di dati dei tassi di cambio. Per il caricamento in blocco, include uno strumento di **importazione CSV** incorporato.

---

## 📝 Editor dei dati

Fai clic sul pulsante **Modifica** (✏️) nella barra degli strumenti del grafico per aprire il pannello dell'editor dei dati:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor dei dati FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Visualizzazione dei dati

L'editor mostra una tabella scorrevole di tutti i punti dati per questa coppia di valute, ordinata per data (dal più recente al più vecchio):

- 📅 **Data** — La data di osservazione
- 💱 **Tasso** — Il valore del tasso di cambio
- 🏛️ **Fonte** — Da dove proviene il dato (nome del provider, importazione CSV o manuale)

### ➕ Aggiunta di un punto dati

1. Fai clic su **Aggiungi** nella parte superiore dell'editor
2. Seleziona la **data** dal selettore di date
3. Inserisci il valore del **tasso**
4. Fai clic su **Salva** — il punto viene aggiunto immediatamente e il grafico si aggiorna

### ✏️ Modifica di un punto dati

1. Fai clic sull'icona della matita accanto a qualsiasi riga
2. Modifica il valore del tasso
3. Fai clic su **Salva** per confermare

### 🗑️ Eliminazione di un punto dati

1. Fai clic sull'icona del cestino accanto a qualsiasi riga
2. Conferma l'eliminazione

!!! warning "I dati sincronizzati sovrascrivono le modifiche manuali"

    Se modifichi o aggiungi manualmente un punto dati per una data che viene successivamente coperta da una sincronizzazione, il valore del provider **sovrascriverà** la tua modifica manuale — il provider è sempre considerato la fonte autorevole. Per le coppie in cui desideri il pieno controllo manuale, usa il provider MANUAL (nessuna fonte di dati automatica) — vedi [Configurazione Provider](provider.md).

---

## 📥 Importazione CSV

Per il caricamento in blocco di dati storici sui tassi, utilizza lo strumento di importazione CSV.

### 🔓 Come accedere

1. Apri l'Editor dei dati (icona della matita ✏️)
2. Fai clic su **Importa CSV** per aprire la finestra di importazione

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Finestra di importazione CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 Formato del file CSV

Il file CSV deve avere **esattamente 2 colonne** con una **riga di intestazione** che specifica la direzione:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Regole

| Regola | Dettagli |
|--------|----------|
| **Separatore** | Punto e virgola (`;`) |
| **Formato data** | `YYYY-MM-DD` |
| **Valori del tasso** | Numeri decimali positivi |
| **Intestazione** | Obbligatoria — deve contenere la direzione (es. `EUR>USD`) |
| **Freccia di direzione** | Usa `>` o `<` (entrambi supportati) |

### ↔️ Direzione nell'intestazione

L'intestazione indica a LibreFolio in quale direzione sono espressi i tassi:

- ➡️ `date;EUR>USD` significa: **1 EUR = X USD** (i tassi sono EUR→USD)
- ⬅️ `date;USD>EUR` significa: **1 USD = X EUR** (i tassi sono USD→EUR)

Se sei sulla pagina EUR/USD e il tuo CSV contiene tassi `USD>EUR`, LibreFolio invertirà automaticamente i valori.

---

### 🔀 Direzione & Scambio

La finestra di importazione mostra una **barra di direzione** che indica come i tuoi dati saranno interpretati:

- ➡️ **Valuta di sinistra** → **Valuta di destra**: il tasso indica quanto della valuta di destra ottieni per 1 unità della valuta di sinistra
- 🔄 Usa il **pulsante di scambio (⇄)** per invertire la direzione se i tuoi dati sono nel formato opposto

L'intestazione del tuo CSV determina automaticamente la direzione. Se l'intestazione è `EUR>USD`, la finestra imposta la direzione su EUR→USD.

---

### 📋 Esempi

#### ✅ File minimo valido

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Direzione invertita

```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

Questo è equivalente al primo esempio — LibreFolio inverte `0.9053` a `1/0.9053 ≈ 1.1045`.

#### ❌ File non valido

```csv
date;GBP>JPY
2024-01-02;188.45
```

Questo fallirà se sei sulla pagina EUR/USD — le valute dell'intestazione devono corrispondere alla coppia della pagina.

---

### ⚠️ Errori comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| **"Le valute dell'intestazione non corrispondono"** | L'intestazione contiene valute non presenti in questa pagina | Controlla la coppia e correggi l'intestazione |
| **"Intestazione mancante o non valida"** | Nessuna riga di intestazione, o formato errato | Aggiungi un'intestazione tipo `date;EUR>USD` |
| **"Date duplicate"** | La stessa data appare più volte | Rimuovi i duplicati |
| **"Tasso non valido"** | Valore non numerico o negativo | Assicurati che tutti i tassi siano numeri positivi |
| **"Formato data non valido"** | La data non è nel formato `YYYY-MM-DD` | Correggi il formato della data |

---

### 🔀 Comportamento di unione

Durante l'importazione via CSV o l'aggiunta manuale di punti nell'editor:

- Le modifiche vengono prima applicate alla **cache locale del client** (visibili immediatamente nel grafico)
- Le modifiche **non vengono salvate** nel database finché non si preme **Salva**
- 🔄 I **punti dati esistenti** nel database verranno **sovrascritti** con i valori importati al salvataggio
- 🆕 Le **nuove date** vengono aggiunte
- ✅ Le **date non presenti nell'importazione** rimangono invariate

!!! tip "Ideale per coppie MANUAL"

    L'editor dati è particolarmente utile per le coppie configurate con il provider MANUAL (nessuna fonte di dati automatica). Per le coppie con provider, le modifiche manuali verranno sovrascritte alla prossima sincronizzazione.
