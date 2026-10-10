# ✏️ Editor dati e importazione CSV

L'editor dati ti consente di aggiungere, modificare ed eliminare i tassi memorizzati di una coppia uno per uno, oppure di caricarne molti in una volta da un file CSV. Niente viene salvato finché non fai clic su **Salva**.

---

## 📝 Apri l'editor

Fai clic su ✏️ (**Modifica tassi**) sul grafico. L'editor si apre sotto il grafico e gli altri pannelli si ripiegano mentre modifichi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor dei dati FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Elenca i tassi del periodo selezionato con la loro **Data**, **Tasso** e **Stato** (**Originale**, **Modificato**, **Eliminato** o **Nuovo**).

- Una data contrassegnata con ⚠️ e con un numero di giorni non ha un tasso proprio (un fine settimana o un giorno festivo) e
  ripete quello precedente. L'interruttore ⚠️ in alto nasconde questi giorni.
- Fai doppio clic su un punto del grafico (pressione prolungata su mobile) per passare alla sua data nell'editor.

---

## ✍️ Modifica i tassi

### ➕ Aggiungi un tasso

Fai clic su **Aggiungi riga**: viene visualizzata una riga il giorno successivo all'ultimo, mai oltre oggi. Se necessario, cambia la sua data con il selettore data, poi digita il tasso.

### ✏️ Modifica un tasso

Fai clic su un tasso e digita il nuovo valore.

### 🗑️ Elimina i tassi

Fai clic sull'icona 🗑️ di una riga, oppure seleziona le righe e fai clic sul cestino in alto. **Ripristina** fa riapparire una riga finché non salvi.

### 💾 Salva le modifiche

Le modifiche vengono mostrate sul grafico come una linea **Anteprima** viola. **Salva (N)** le scrive tutte; **Annulla** le scarta. Un tasso deve essere maggiore di zero: uno pari a zero, negativo o vuoto viene ignorato.

!!! warning "I dati sincronizzati sovrascrivono le modifiche manuali"

    Una successiva sincronizzazione delle stesse date sostituisce i tuoi valori con quelli del provider. Per avere il pieno controllo manuale, usa una coppia senza provider — vedi [Configurazione provider](provider.md).

---

## 📥 Importazione CSV

### 🔓 Apri la finestra di importazione

1. Nell'editor, fai clic su **Importa CSV**.
2. In **Dati di importazione CSV**, trascina un file `.csv` o `.txt`, oppure incolla il testo nella casella.
3. Controlla la direzione in alto, poi fai clic su **Importa (N)**.

Le righe vengono aggiunte all'editor: esaminale, poi fai clic su **Salva**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Finestra di importazione CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
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
| **Tassi** | Numeri positivi; `.` o `,` come separatore decimale, `_` opzionale per le migliaia (`1_000.50`) |

### ↔️ Direzione

- `EUR>USD` significa **1 EUR = X USD**; `EUR<USD` è il contrario, **1 USD = X EUR**.
- L'intestazione deve indicare le due valute di questa coppia, in qualsiasi ordine.
- La barra in alto mostra come vengono letti i tassi (*Tassi interpretati come: 1 EUR = X USD*); ⇄ inverte la direzione e riscrive l'intestazione.
- Un file nella direzione opposta a quella della pagina viene invertito automaticamente: ogni tasso $r$ diventa $1/r$.

??? example "📋 Esempi — gli stessi tassi scritti in entrambe le direzioni"

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

    Nella pagina EUR/USD entrambi i file danno gli stessi tassi: `0.9053` diventa $1/0.9053 \approx 1.1046$.

### ⚠️ Errori comuni

La finestra di importazione contrassegna ogni riga errata; vengono importate solo le righe valide.

| Messaggio | Causa | Correzione |
|---------|-------|-----|
| **Le valute dell'intestazione non corrispondono** | Altre valute nell'intestazione, ad es. `GBP>JPY` nella pagina EUR/USD | Usa le valute di questa coppia |
| **Intestazione prevista** o **Colonne obbligatorie mancanti** | Nessuna riga di intestazione, o una colonna mancante | Inizia con una riga come `date;EUR>USD` |
| **Formato data non valido** | La data non è `YYYY-MM-DD` | Correggi la data |
| **Numero non valido** | Il tasso non è un numero | Correggi il valore |
| **Data duplicata** | La stessa data compare due volte | Mantieni una riga per data |

??? info "🔀 Come si uniscono le righe importate — quando l'editor ha già alcune delle date"

    - Una data già presente nell'editor assume il tasso importato (**Modificato**); una nuova data viene aggiunta
      (**Nuovo**). Le date mancanti dal file restano come sono.
    - Anche le date al di fuori del periodo selezionato vengono salvate, sostituendo qualsiasi tasso memorizzato in quei giorni;
      dopo il salvataggio, il periodo si amplia per mostrarle.
