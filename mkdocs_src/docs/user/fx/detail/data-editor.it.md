# ✏️ Editor dati e importazione CSV

L'editor dati permette di aggiungere, modificare ed eliminare una alla volta le quotazioni memorizzate di una coppia, oppure di caricarne molte in una sola volta da un file CSV. Nulla viene salvato finché non fai clic su **Salva**.

---

## 📝 Aprire l'editor

Fai clic su ✏️ (**Modifica quotazioni**) nel grafico. L'editor si apre sotto il grafico e gli altri pannelli si ripiegano mentre modifichi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor dati FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Elenca le quotazioni del periodo selezionato con la loro **Data**, **Quotazione** e **Stato** (**Originale**, **Modificata**, **Eliminata** o **Nuova**).

- Una data contrassegnata con ⚠️ e con un numero di giorni non ha una quotazione propria (un fine settimana o un giorno festivo) e ripete quella precedente. L'interruttore ⚠️ in alto nasconde questi giorni.
- Fai doppio clic su un punto del grafico (pressione prolungata su mobile) per passare alla sua data nell'editor.

---

## ✍️ Modificare le quotazioni

### ➕ Aggiungere una quotazione

Fai clic su **Aggiungi riga**: compare una riga nel giorno successivo all'ultimo, mai oltre oggi. Se serve, cambiane la data con il selettore di data, poi digita la quotazione.

### ✏️ Modificare una quotazione

Fai clic su una quotazione e digita il nuovo valore.

### 🗑️ Eliminare le quotazioni

Fai clic su 🗑️ su una riga, oppure seleziona le righe e fai clic sul cestino in alto. **Ripristina** riporta indietro una riga finché non salvi.

### 💾 Salvare le modifiche

Le tue modifiche compaiono sul grafico come linea viola **Anteprima**. **Salva (N)** le scrive tutte; **Annulla** le scarta. Una quotazione deve essere maggiore di zero: una quotazione zero, negativa o vuota viene ignorata. Una quotazione che il database non può memorizzare — più di 14 cifre prima del separatore decimale, o inferiore a 0.0000000001 — viene rifiutata al salvataggio e non viene memorizzata. Il limite si applica alla quotazione così come è memorizzata: LibreFolio memorizza ogni coppia con le valute in ordine alfabetico, quindi nella pagina USD/EUR si applica a 1 ÷ la quotazione che digiti.

Se il server rifiuta alcune delle tue quotazioni, ad esempio una quotazione troppo grande o troppo piccola per essere memorizzata, salva le altre. Un avviso elenca quindi fino a cinque date rifiutate, ciascuna con il proprio motivo, e conta le restanti; rimane per 20 secondi, così puoi annotarle e reinserirle. Se rifiuta l'intero salvataggio, ad esempio perché una data è successiva a domani, o perché nessuna delle quotazioni può essere memorizzata, nulla viene salvato: il messaggio spiega il motivo e l'editor resta aperto con le tue modifiche.

!!! warning "I dati sincronizzati sovrascrivono le modifiche manuali"

    Una successiva sincronizzazione delle stesse date sostituisce i tuoi valori con quelli del provider. Per avere il pieno controllo manuale, usa una coppia senza provider — vedi [Configurazione provider](provider.md).

---

## 📥 Importazione CSV

### 🔓 Aprire la finestra di importazione

1. Nell'editor, fai clic su **Importa CSV**.
2. In **Importa dati CSV**, trascina un file `.csv` o `.txt`, oppure incolla il testo nella casella.
3. Controlla la direzione in alto, poi fai clic su **Importa (N)**.

Le righe si aggiungono all'editor: controllale, poi fai clic su **Salva**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Finestra modale di importazione CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📄 Formato del file

Due colonne, con una riga di intestazione che imposta la direzione:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

| Regola | Dettagli |
|------|---------|
| **Separatore** | Punto e virgola (`;`) |
| **Intestazione** | `date` e la direzione, ad es. `EUR>USD` |
| **Date** | `YYYY-MM-DD` |
| **Quotazioni** | Numeri positivi; `.` o `,` come separatore decimale, `_` facoltativo per le migliaia (`1_000.50`) |

### ↔️ Direzione

- `EUR>USD` significa **1 EUR = X USD**; `EUR<USD` è il contrario, **1 USD = X EUR**.
- L'intestazione deve indicare le due valute di questa coppia, in qualsiasi ordine.
- La barra in alto mostra come vengono lette le quotazioni (*Quotazioni interpretate come: 1 EUR = X USD*); ⇄ ne inverte il verso e riscrive l'intestazione.
- Un file nella direzione opposta alla pagina viene invertito per te: ogni quotazione $r$ diventa $1/r$.

??? example "📋 Esempi — le stesse quotazioni scritte in entrambe le direzioni"

    ```csv
    date;EUR>USD
    2024-01-02;1.1045
    2024-01-03;1.0982
    ```

    ```csv
    date;USD>EUR
    2024-01-02;0.9053
    2024-01-03;0.9106
    ```

    Nella pagina EUR/USD entrambi i file danno le stesse quotazioni: `0.9053` diventa $1/0.9053 \approx 1.1046$.

### ⚠️ Errori comuni

La finestra di importazione segnala ogni riga errata; vengono importate solo le righe valide.

| Messaggio | Causa | Correzione |
|---------|-------|-----|
| **Le valute dell'intestazione non corrispondono** | Altre valute nell'intestazione, ad es. `GBP>JPY` nella pagina EUR/USD | Usa le valute di questa coppia |
| **Intestazione attesa** o **Colonne obbligatorie mancanti** | Nessuna riga di intestazione, o una colonna mancante | Inizia con una riga come `date;EUR>USD` |
| **Formato data non valido** | La data non è `YYYY-MM-DD` | Correggi la data |
| **Numero non valido** | La quotazione non è un numero | Correggi il valore |
| **Data duplicata** | La stessa data compare due volte | Mantieni una sola riga per data |

??? info "🔀 Come si uniscono le righe importate — quando l'editor ha già alcune delle date"

    - Una data già presente nell'editor assume la quotazione importata (**Modificata**); una nuova data viene aggiunta (**Nuova**). Le date assenti dal file restano come sono.
    - Anche le date al di fuori del periodo selezionato vengono salvate, sostituendo qualsiasi quotazione memorizzata in quei giorni; dopo il salvataggio, il periodo si amplia per mostrarle.
