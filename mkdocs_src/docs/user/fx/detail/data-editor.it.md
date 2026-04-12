# ✏️ Editor Dati e Importazione CSV

L'Editor Dati ti permette di **visualizzare, aggiungere, modificare ed eliminare** singoli punti dati del tasso di cambio. Per il caricamento massivo, include uno strumento integrato di **Importazione CSV**.

---

## 📝 Editor Dati

Fai clic sul pulsante **Modifica** (✏️) nella barra degli strumenti del grafico per aprire il pannello dell'editor dati:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="FX Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Visualizzazione Dati

L'editor mostra una tabella scorrevole di tutti i punti dati per questa coppia di valute, ordinati per data (dal più recente):

- 📅 **Data** — La data di osservazione
- 💱 **Tasso** — Il valore del tasso di cambio
- 🏛️ **Fonte** — L'origine dei dati (nome del provider, importazione CSV o manuale)

### ➕ Aggiungere un Punto Dato

1. Fai clic su **"Aggiungi"** nella parte superiore dell'editor
2. Seleziona la **data** dal selettore di date
3. Inserisci il valore del **tasso**
4. Fai clic su **Salva** — il punto viene aggiunto immediatamente e il grafico si aggiorna

### ✏️ Modificare un Punto Dato

1. Fai clic sull'**icona della matita** accanto a qualsiasi riga
2. Modifica il valore del tasso
3. Fai clic su **Salva** per confermare

### 🗑️ Eliminare un Punto Dato

1. Fai clic sull'**icona del cestino** accanto a qualsiasi riga
2. Conferma l'eliminazione

!!! warning "I dati sincronizzati sovrascrivono le modifiche manuali"

    Se modifichi o aggiungi manualmente un punto dato per una data che viene successivamente coperta da una sincronizzazione, il valore del provider **sovrascriverà** la tua modifica manuale — il provider è sempre considerato la fonte autorevole. Per le coppie per le quali desideri un controllo manuale completo, utilizza il provider MANUAL (nessuna fonte dati automatica) — vedi [Provider Config](provider.md).

---

## 📥 Importazione CSV

Per il caricamento massivo di dati storici dei tassi, utilizza lo strumento di Importazione CSV.

### 🔓 Come Accedere

1. Apri l'Editor Dati (icona matita ✏️)
2. Fai clic su **"Importa CSV"** per aprire la finestra modale di importazione

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="CSV Import Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 Formato File CSV

Il file CSV deve avere **esattamente 2 colonne** con una **riga di intestazione** che specifichi la direzione:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Regole

| Regola | Dettagli |
|------|---------|
| **Separatore** | Punto e virgola (`;`) |
| **Formato data** | `YYYY-MM-DD` |
| **Valori tasso** | Numeri decimali positivi |
| **Intestazione** | Obbligatoria — deve contenere la direzione (es. `EUR>USD`) |
| **Freccia direzione** | Usa `>` o `<` (entrambe sono supportate) |

### ↔️ Direzione nell'Intestazione

L'intestazione indica a LibreFolio in quale direzione sono espressi i tassi:

- ➡️ `date;EUR>USD` significa: **1 EUR = X USD** (i tassi sono EUR→USD)
- ⬅️ `date;USD>EUR` significa: **1 USD = X EUR** (i tassi sono USD→EUR)

Se ti trovi nella pagina EUR/USD e il tuo CSV ha tassi `USD>EUR`, LibreFolio invertirà automaticamente i valori.

---

### 🔀 Direzione e Swap

La finestra modale di importazione mostra una **barra della direzione** che indica come verranno interpretati i tuoi dati:

- ➡️ **Valuta sinistra** → **Valuta destra**: il tasso indica la quantità di valuta di destra ottenibile per 1 unità della valuta di sinistra
- 🔄 Usa il **pulsante di swap (⇄)** per invertire la direzione se i tuoi dati sono nel formato opposto

L'intestazione nel tuo CSV determina la direzione automaticamente. Se l'intestazione riporta `EUR>USD`, la modale imposta la direzione su EUR→USD.

---

### 📋 Esempi

#### ✅ File Valido Minimo

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Direzione Invertita

```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

Questo è equivalente al primo esempio — LibreFolio inverte `0.9053` in `1/0.9053 ≈ 1.1045`.

#### ❌ File Non Valido

```csv
date;GBP>JPY
2024-01-02;188.45
```

Questo fallirà se ti trovi nella pagina EUR/USD — le valute nell'intestazione devono corrispondere alla coppia della pagina.

---

### ⚠️ Errori Comuni

| Errore | Causa | Soluzione |
|-------|-------|-----|
| **"Header currencies don't match"** | L'intestazione ha valute non presenti in questa pagina | Verifica la coppia di valute e correggi l'intestazione |
| **"Missing or invalid header"** | Manca la riga di intestazione o il formato è errato | Aggiungi un'intestazione come `date;EUR>USD` |
| **"Duplicate dates"** | La stessa data appare più volte | Rimuovi i duplicati |
| **"Invalid rate"** | Valore non numerico o negativo | Assicurati che tutti i tassi siano numeri positivi |
| **"Invalid date format"** | Data non nel formato `YYYY-MM-DD` | Correggi la formattazione della data |

---

### 🔀 Comportamento di Merge

Quando importi tramite CSV o aggiungi punti manualmente nell'editor:

- Le modifiche vengono prima applicate alla **cache locale del client** (visibili immediatamente nel grafico)
- Le modifiche **non vengono salvate** nel database finché non fai clic su **Salva**
- 🔄 I **punti dati esistenti** nel database verranno **sovrascritti** con i valori importati al momento del salvataggio
- 🆕 Le **nuove date** vengono aggiunte
- ✅ Le **date non presenti nell'importazione** rimangono invariate

Ciò ti consente di aggiornare selettivamente intervalli di date specifici senza influire sul resto dei tuoi dati.

!!! tip "Ideale per coppie MANUAL"

    L'editor dati è più utile per le coppie configurate con il provider MANUAL (nessuna fonte dati automatica). Per le coppie basate su un provider, le modifiche manuali verranno sovrascritte alla successiva sincronizzazione.
