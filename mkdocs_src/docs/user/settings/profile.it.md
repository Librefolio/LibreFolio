# 👤 Profilo

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="profile" alt="Profilo">
</div>

La scheda **Profilo** gestisce la tua **identità** in LibreFolio: chi sei e come accedi. Le scelte di visualizzazione (lingua, valuta, tema) si trovano invece in **[Preferenze](preferences.md)**; le opzioni a livello di istanza si trovano nella **[scheda Admin](../../admin/settings.md)**.

## 🔒 Blocco di modifica

La scheda si apre **bloccata**: i campi sono di sola lettura finché non fai clic sul pulsante ✏️ **matita** nell'intestazione. Questo evita modifiche accidentali. Se blocchi di nuovo la scheda con modifiche non salvate, una finestra di conferma chiede se desideri scartarle.

Quando la scheda è sbloccata, ogni campo modificato mostra i propri pulsanti **salva** / **annulla** e l'intestazione offre **salva tutto** e **annulla tutto** per azioni in blocco.

## 🖼️ Avatar

Passa il mouse sull'avatar (mentre la scheda è sbloccata) e fai clic sull'overlay della fotocamera 📷 per aprire il selettore di immagini: scegli un'immagine esistente dalla [libreria Files](../files/index.md) oppure caricane una nuova. I caricamenti passano attraverso lo **[strumento di ritaglio immagini](../misc/image-crop.md)** con il preset *avatar* (ritaglio quadrato, anteprima circolare).

L'avatar viene salvato immediatamente e viene utilizzato in tutta l'app ovunque venga mostrata la tua identità: barra laterale, condivisione dei broker ed elenchi dei collaboratori.

## ✏️ Nome utente, Email e Account creato

- **Nome utente** e **Email** sono modificabili (è necessario sbloccare la scheda). Le modifiche vengono applicate subito alle tue credenziali di accesso.
- **Account creato** è un campo di sola lettura che mostra la data di registrazione.

## 🔐 Sicurezza

### 🔑 Cambia password

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Cambia password">
</div>

Il pulsante **Cambia password** (sempre disponibile, non richiede lo sblocco) apre una finestra modale che richiede:

1. La tua **password attuale** (per verifica)
2. Una **nuova password** che soddisfi tutte le regole: minimo 8 caratteri, almeno una lettera maiuscola, una lettera minuscola, un numero e un carattere speciale — e deve essere diversa da quella attuale
3. La **conferma** della nuova password

Dopo la conferma, la tua sessione rimane attiva: non devi accedere di nuovo.

### 🗑️ Elimina account

Il pulsante **Elimina account** rimuove definitivamente il tuo utente e tutto ciò che possiede. Per confermare, devi digitare il tuo **nome utente** nella finestra di dialogo. L'eliminazione è immediata: vieni disconnesso e riportato alla pagina di accesso.

!!! warning "Irreversibile"

    L'eliminazione dell'account non può essere annullata: i tuoi broker, le transazioni e le impostazioni vengono rimossi insieme all'account. Se sei l'**unico amministratore** dell'istanza, l'eliminazione viene rifiutata: promuovi prima un altro utente.

---

## 🔗 Correlati

- 🎛️ **[Preferenze utente](preferences.md)** — Lingua, valuta base e tema
- ⚙️ **[Panoramica delle impostazioni](index.md)** — Riepilogo generale delle impostazioni
- ℹ️ **[Informazioni](about.md)** — Informazioni sulla versione, sui plugin e sul changelog
- 🛡️ **[Impostazioni globali](../../admin/settings.md)** — Opzioni a livello di istanza (admin)
